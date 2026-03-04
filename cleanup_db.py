#!/usr/bin/env python3
"""
Clean database to only contain invoices with existing PDF files.
Then renumber all invoices properly.
"""

import re
from pathlib import Path
from src.database import get_connection

def cleanup_database():
    """Remove database records for PDFs that don't exist on disk."""
    pdf_dir = Path("invoices/pdf")
    
    # Get all actual PDF files
    existing_pdfs = set()
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            existing_pdfs.add(pdf_file.name)
    
    # Get all database records
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, invoice_number, pdf_path FROM invoices")
    all_records = cur.fetchall()
    
    # Find records to delete (where PDF doesn't exist)
    to_delete = []
    for inv_id, invoice_number, pdf_path in all_records:
        if pdf_path:
            pdf_name = Path(pdf_path).name
            if pdf_name not in existing_pdfs:
                to_delete.append((inv_id, invoice_number, pdf_path))
    
    if to_delete:
        print(f"Found {len(to_delete)} database records with missing PDF files:")
        for inv_id, inv_num, pdf_path in to_delete:
            print(f"  {inv_num:<20} -> {pdf_path}")
        
        response = input("\nDelete these records from database? (yes/no): ").strip().lower()
        if response == "yes":
            for inv_id, _, _ in to_delete:
                cur.execute("DELETE FROM invoices WHERE id = ?", (inv_id,))
            conn.commit()
            print(f"Deleted {len(to_delete)} records.")
        else:
            print("Cancelled.")
            conn.close()
            return False
    else:
        print("No orphaned database records found.")
    
    conn.close()
    return True

if __name__ == "__main__":
    print("Database Cleanup")
    print("=" * 60)
    print()
    cleanup_database()
