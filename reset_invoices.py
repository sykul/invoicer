#!/usr/bin/env python3
"""
Safely reset all invoices and prepare to re-issue from CSV.

This script:
1. Deletes all invoice PDFs from invoices/pdf/
2. Clears all invoice records from the database
3. Clears all InvoiceNumber entries from the CSV (marks them for re-billing)

After running this, you can safely run `issue_all()` to generate fresh invoices
with correct numbering starting from 0001 for each month.

IMPORTANT: This is destructive! Use only for testing/development.
"""

import shutil
import csv
from pathlib import Path
from src.database import get_connection

def reset_invoices():
    """Reset all three data sources: PDFs, database, and CSV."""
    
    print("Invoice Reset Tool")
    print("=" * 70)
    print()
    print("This will:")
    print("  1. DELETE all PDF files from invoices/pdf/")
    print("  2. DELETE all invoice records from database")
    print("  3. CLEAR InvoiceNumber from CSV (mark for re-billing)")
    print()
    print("After this, you can run issue_all() to regenerate invoices with")
    print("correct numbering (0001-based per month).")
    print()
    
    response = input("Are you sure? Type 'YES I UNDERSTAND' to proceed: ").strip()
    if response != "YES I UNDERSTAND":
        print("Cancelled.")
        return
    
    # Step 1: Delete all PDFs
    print()
    print("Deleting PDFs from invoices/pdf/...")
    pdf_dir = Path("invoices/pdf")
    if pdf_dir.exists():
        # Keep directory structure, just delete PDF files
        pdf_files = list(pdf_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            pdf_file.unlink()
            print(f"  Deleted: {pdf_file.name}")
        if not pdf_files:
            print("  (no PDF files found)")
    
    # Step 2: Clear database
    print()
    print("Clearing invoice records from database...")
    conn = get_connection()
    cur = conn.cursor()
    
    # Get count before deletion
    cur.execute("SELECT COUNT(*) FROM invoices")
    count = cur.fetchone()[0]
    
    # Delete all invoice records
    cur.execute("DELETE FROM invoices")
    conn.commit()
    conn.close()
    print(f"  Deleted {count} invoice record(s)")
    
    # Step 3: Clear CSVactivities.csv
    print()
    print("Clearing InvoiceNumber from CSV...")
    activities_file = Path("data/activities.csv")
    
    if activities_file.exists():
        # Read CSV
        with open(activities_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        # Clear InvoiceNumber column
        cleared_count = 0
        for row in rows:
            if row.get("InvoiceNumber", "").strip():
                row["InvoiceNumber"] = ""
                cleared_count += 1
        
        # Write back
        with open(activities_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"  Cleared InvoiceNumber from {cleared_count} row(s)")
    else:
        print("  (activities.csv not found)")
    
    print()
    print("✓ Reset complete!")
    print()
    print("Next steps:")
    print("  1. Run: from src.invoice_service import issue_all")
    print("  2. Then: issue_all()")
    print()
    print("This will regenerate invoices with correct month-based numbering")
    print("(0001, 0002, etc. starting fresh each month).")

if __name__ == "__main__":
    reset_invoices()
