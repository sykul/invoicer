#!/usr/bin/env python3
"""
Fix invoice numbering to reset the counter each month.

Currently PDF files on disk have incorrect numbering that doesn't reset monthly.
This script:
1. Reads actual PDF files from disk
2. Renumbers them to start from 0001 for each month
3. Updates the database records
4. Renames PDF files to match

Example:
  facture_202311-0003_Sibois.pdf -> facture_202311-0001_Sibois.pdf
  facture_202311-0004_Legrand.pdf -> facture_202311-0002_Legrand.pdf
  etc.
"""

import re
from pathlib import Path
from .database import get_connection

def scan_pdf_files():
    """
    Scan invoices/pdf directory for actual PDF files.
    Returns: dict mapping old_invoice_key -> (pdf_filename, surname)
    """
    pdf_dir = Path("invoices/pdf")
    existing_pdfs = {}  # Maps "YYYYMM-XXXX" -> (filename, surname)
    
    if not pdf_dir.exists():
        print("ERROR: invoices/pdf directory not found!")
        return existing_pdfs
    
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        # Parse filename: facture_YYYYMM-XXXX_SURNAME.pdf
        match = re.search(r"facture_(\d{6}-\d{4})_(.+)\.pdf$", pdf_file.name)
        if match:
            invoice_key = match.group(1)  # YYYYMM-XXXX
            surname = match.group(2)      # SURNAME
            existing_pdfs[invoice_key] = (pdf_file.name, surname)
    
    return existing_pdfs

def renumber_invoices():
    """
    Renumber all invoices from actual PDF files so counter resets each month.
    Returns: list of update dicts with old_key, new_key, old_filename, new_filename
    """
    existing_pdfs = scan_pdf_files()
    
    if not existing_pdfs:
        print("No PDF files found in invoices/pdf directory.")
        return []
    
    # Group by year-month
    groups_by_month = {}
    
    for old_invoice_key, (pdf_filename, surname) in existing_pdfs.items():
        year_month = old_invoice_key[:6]  # YYYYMM
        old_seq = int(old_invoice_key[-4:])  # XXXX
        
        if year_month not in groups_by_month:
            groups_by_month[year_month] = []
        
        groups_by_month[year_month].append({
            "old_invoice_key": old_invoice_key,
            "old_seq": old_seq,
            "pdf_filename": pdf_filename,
            "surname": surname
        })
    
    # Renumber within each month
    updates = []
    for year_month in sorted(groups_by_month.keys()):
        invoices_in_month = groups_by_month[year_month]
        # Sort by old sequence number to maintain chronological order
        invoices_in_month.sort(key=lambda x: x["old_seq"])
        
        for new_seq, invoice_data in enumerate(invoices_in_month, start=1):
            old_invoice_key = invoice_data["old_invoice_key"]
            new_invoice_key = f"{year_month}-{new_seq:04d}"
            
            if old_invoice_key != new_invoice_key:
                old_filename = invoice_data["pdf_filename"]
                new_filename = f"facture_{new_invoice_key}_{invoice_data['surname']}.pdf"
                
                updates.append({
                    "old_invoice_key": old_invoice_key,
                    "new_invoice_key": new_invoice_key,
                    "old_filename": old_filename,
                    "new_filename": new_filename
                })
    
    return updates

def apply_renumbering(updates):
    """Apply renumbering to database and rename PDF files."""
    if not updates:
        print("No changes needed - all invoices are already correctly numbered.")
        return
    
    print(f"Will renumber {len(updates)} invoice(s):\n")
    
    # Show changes grouped by month for clarity
    changes_by_month = {}
    for update in updates:
        month = update['new_invoice_key'][:6]
        if month not in changes_by_month:
            changes_by_month[month] = []
        changes_by_month[month].append(update)
    
    for month in sorted(changes_by_month.keys()):
        print(f"  {month}:")
        for update in changes_by_month[month]:
            print(f"    {update['old_invoice_key']} -> {update['new_invoice_key']}")
    
    # Ask for confirmation
    print()
    response = input("Apply these changes? (yes/no): ").strip().lower()
    if response != "yes":
        print("Cancelled.")
        return
    
    # Rename PDF files first
    pdf_dir = Path("invoices/pdf")
    for update in updates:
        old_filename = update["old_filename"]
        new_filename = update["new_filename"]
        
        old_path = pdf_dir / old_filename
        new_path = pdf_dir / new_filename
        
        if not old_path.exists():
            print(f"WARNING: PDF not found: {old_path}")
            continue
        
        if new_path.exists():
            print(f"ERROR: Target file already exists: {new_path}")
            return
        
        old_path.rename(new_path)
        print(f"Renamed: {old_filename} -> {new_filename}")
    
    # Update database
    conn = get_connection()
    cur = conn.cursor()
    
    for update in updates:
        old_key = update["old_invoice_key"]
        new_key = update["new_invoice_key"]
        new_filename = update["new_filename"]
        
        # Find invoice by old number
        cur.execute("SELECT id FROM invoices WHERE invoice_number = ?", (old_key,))
        row = cur.fetchone()
        
        if not row:
            # This PDF doesn't have a database record - skip it or create one
            print(f"WARNING: No database record for {old_key}")
            continue
        
        inv_id = row[0]
        
        # Check if new invoice number already exists
        cur.execute("SELECT id FROM invoices WHERE invoice_number = ?", (new_key,))
        if cur.fetchone():
            print(f"ERROR: Invoice number {new_key} already exists in database!")
            conn.close()
            return
        
        # Update database with new invoice number and new PDF path
        new_pdf_path = f"invoices/pdf/{new_filename}"
        cur.execute("""
            UPDATE invoices
            SET invoice_number = ?, pdf_path = ?
            WHERE id = ?
        """, (new_key, new_pdf_path, inv_id))
    
    conn.commit()
    conn.close()
    
    print(f"\nSuccessfully renumbered {len(updates)} invoice(s) and updated database.")

def main():
    """Main entry point."""
    print("Invoice Numbering Fixer")
    print("=" * 60)
    print()
    
    updates = renumber_invoices()
    apply_renumbering(updates)

if __name__ == "__main__":
    main()

