#!/usr/bin/env python3
"""
Recreate database records from actual PDF files.
"""

import re
from pathlib import Path
from src.database import get_connection
from src.client_service import get_client_by_name

def recreate_invoice_records():
    """
    Scan PDF directory and create/update database records.
    """
    pdf_dir = Path("invoices/pdf")
    
    if not pdf_dir.exists():
        print("ERROR: invoices/pdf directory not found!")
        return
    
    # Find all invoice PDFs
    invoice_pdfs = []
    for pdf_file in sorted(pdf_dir.glob("facture_*.pdf")):
        # Parse: facture_YYYYMM-XXXX_SURNAME.pdf
        match = re.search(r"facture_(\d{6}-\d{4})_(.+)\.pdf$", pdf_file.name)
        if match:
            invoice_number = match.group(1)
            surname = match.group(2)
            invoice_pdfs.append({
                "invoice_number": invoice_number,
                "surname": surname,
                "filename": pdf_file.name,
                "filepath": str(pdf_file)
            })
    
    if not invoice_pdfs:
        print("No invoice PDFs found!")
        return
    
    print(f"Found {len(invoice_pdfs)} invoice PDFs to process")
    
    # Get all clients for lookup
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM clients")
    clients_by_name = {row[1]: row[0] for row in cur.fetchall()}
    
    # For each PDF, find matching client and create/update record
    created = 0
    skipped = 0
    
    for pdf_info in invoice_pdfs:
        invoice_number = pdf_info["invoice_number"]
        surname = pdf_info["surname"]
        filepath = pdf_info["filepath"]
        
        # Check if record exists
        cur.execute("SELECT id FROM invoices WHERE invoice_number = ?", (invoice_number,))
        existing = cur.fetchone()
        
        if existing:
            # Update the pdf_path
            cur.execute("""
                UPDATE invoices
                SET pdf_path = ?
                WHERE invoice_number = ?
            """, (filepath, invoice_number))
            created += 1
        else:
            # Try to find matching client by surname
            # First try exact match, then fuzzy
            client_id = None
            
            # Look for client whose LegalName ends with this surname
            for client_name, cid in clients_by_name.items():
                if client_name.lower().endswith(surname.lower()) or surname.lower() in client_name.lower():
                    client_id = cid
                    break
            
            if not client_id:
                print(f"WARNING: Skipping {invoice_number} - cannot find client for surname '{surname}'")
                skipped += 1
                continue
            
            # Create record with default values
            cur.execute("""
                INSERT INTO invoices (invoice_number, client_id, issue_date, total, pdf_path, hash)
                VALUES (?, ?, '2026-03-04', 0, ?, '')
            """, (invoice_number, client_id, filepath))
            created += 1
    
    conn.commit()
    conn.close()
    
    print(f"Created/updated {created} invoice records")
    if skipped > 0:
        print(f"Skipped {skipped} records due to missing clients")

if __name__ == "__main__":
    print("Recreate Invoice Records from PDFs")
    print("=" * 60)
    print()
    recreate_invoice_records()
