# Safe Testing & Reset Guide

## The Issue (Now Fixed)

When testing the invoicing script, you might delete PDFs and CSV records to start fresh. However, if you don't also delete the **database records**, the numbering function will still see old invoice numbers and continue from the previous maximum instead of resetting to 0001 for each month.

**Example of what went wrong:**
```
Database still has: 202311-0003, 202311-0004
You delete PDFs and CSV records
Run issue_all() again
→ New invoices get numbered: 202311-0005, 202311-0006 ❌ (should be 0001, 0002)
```

## The Solution: Three-Part Reset

To safely reset and test, all three data sources must be synchronized:

1. **PDFs** - Delete from `invoices/pdf/`
2. **Database** - Clear from `invoices` table
3. **CSV** - Clear `InvoiceNumber` column in `data/activities.csv`

## How to Reset Safely

### Method 1: Automatic Reset Script (Recommended)

```bash
python reset_invoices.py
```

This script will:
- ✓ Delete all PDFs
- ✓ Clear all database records
- ✓ Unmark all activities in CSV (set `InvoiceNumber` to empty)

It asks for confirmation first, so you won't accidentally delete anything.

### Method 2: Manual Reset

If you prefer to do it manually:

```python
# Delete all PDFs
rm invoices/pdf/*.pdf

# Clear database
python -c "from src.database import get_connection; conn = get_connection(); conn.execute('DELETE FROM invoices'); conn.commit(); conn.close(); print('Database cleared')"

# Clear CSV (using the script or manually edit it)
```

Then edit `data/activities.csv` and clear the `InvoiceNumber` column for all rows.

## Testing Workflow

1. **Reset everything:**
   ```bash
   python reset_invoices.py
   ```

2. **Re-generate invoices:**
   ```bash
   python -c "from src.invoice_service import issue_all; issue_all()"
   ```

3. **Verify numbering is correct:**
   ```bash
   ls -la invoices/pdf/ | grep facture
   ```
   
   You should see:
   ```
   facture_202311-0001_Client.pdf
   facture_202311-0002_Client.pdf
   facture_202312-0001_Client.pdf
   facture_202312-0002_Client.pdf
   ...etc
   ```

4. **Check database matches PDFs:**
   ```bash
   python -c "
   from src.database import get_connection
   conn = get_connection()
   cur = conn.cursor()
   cur.execute('SELECT COUNT(*) FROM invoices')
   print(f'DB records: {cur.fetchone()[0]}')
   conn.close()
   "
   ```
   
   Should show the same number of records as PDF files.

## Why This Happens

The `get_next_invoice_number()` function in `src/numbering.py` works by:

1. Querying the database for invoices matching the month
2. Finding the maximum sequence number
3. Adding 1 for the next invoice

If the database still has old records, step 2 will find the old max and increment from there, bypassing the monthly reset.

## Prevention

- **Always use `reset_invoices.py`** when testing
- **Don't manually delete** PDFs or CSV rows without synchronizing the database
- Consider running database consistency checks if you're doing manual edits

## Consistency Checks

To verify everything is synchronized:

```python
from pathlib import Path
from src.database import get_connection

# Check PDFs vs Database
pdf_dir = Path("invoices/pdf")
pdf_count = len(list(pdf_dir.glob("facture_*.pdf")))

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE 'facture_%'")
db_count = cur.fetchone()[0]
conn.close()

print(f"PDFs: {pdf_count}, DB: {db_count}")
assert pdf_count == db_count, "Mismatch! Use reset_invoices.py"
```
