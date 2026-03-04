from datetime import datetime
from .database import get_connection

def get_next_invoice_number(service_year: int = None, service_month: int = None):
    """
    Generate next invoice number in format YYYYMM-XXXX
    Sequence resets each month (0001, 0002, 0003, etc.).
    
    Args:
        service_year: Year of service (if None, uses current year)
        service_month: Month of service (if None, uses current month)
    
    Returns invoice number with service month prefix, not issue date prefix.
    
    IMPORTANT: This function queries the database for existing invoice numbers.
    If manually testing and deleting invoices, you MUST:
    1. Delete PDFs from invoices/pdf/
    2. Clear database records with: DELETE FROM invoices
    3. Clear InvoiceNumber from CSV
    
    Use reset_invoices.py to do all three safely at once.
    """
    if service_year is None or service_month is None:
        now = datetime.now()
        service_year = now.year
        service_month = now.month
    
    year_month = f"{service_year:04d}{service_month:02d}"  # e.g., 202602

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT invoice_number FROM invoices WHERE invoice_number LIKE ?", (f"{year_month}-%",))
    numbers = cur.fetchall()
    conn.close()

    seq = 1
    if numbers:
        seq = max(int(n[0].split("-")[1]) for n in numbers) + 1

    return f"{year_month}-{seq:04d}"  # e.g., 202602-0001