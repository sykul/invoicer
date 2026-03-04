import csv
import difflib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .database import get_connection
from .client_service import get_client_by_name
from .facturx_generator import embed_facturx
from .pdf_generator import generate_pdf
from .config_service import get_config
from .numbering import get_next_invoice_number
from .models import InvoiceLine, Invoice
from .utils import sha256_file

ACTIVITIES_FILE = "data/activities.csv"


def is_activity_in_completed_month(activity_date_str: str, row_index: int) -> bool:
    """
    Check if an activity date falls in a completed calendar month.
    
    An activity is billable only if its date is strictly before the first day
    of the current month (unless invoice_only_completed_months is false).
    
    Returns: True if activity should be considered for invoicing, False otherwise.
    Handles date parsing errors gracefully.
    """
    config = get_config()
    enforce_completed_months = config.get("invoice_only_completed_months", True)
    
    # If flag is false, all dates are billable
    if not enforce_completed_months:
        return True
    
    try:
        activity_date = datetime.strptime(activity_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        print(f"Row {row_index}: Invalid date format '{activity_date_str}'. Expected YYYY-MM-DD. Skipping row.")
        return False
    
    # Get first day of current month
    today = datetime.now()
    first_day_of_current_month = datetime(today.year, today.month, 1).date()
    
    # Activity must be strictly before the first day of current month
    if activity_date >= first_day_of_current_month:
        return False
    
    return True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_client_with_fuzzy_support(name: str) -> Optional[tuple]:
    """
    Find a client by name with fuzzy matching support.
    
    1. Attempt exact case-insensitive match.
    2. If no match, use difflib.get_close_matches().
    3. Print suggestions or not found error.
    
    Returns: client_row from database or None if not found.
    """
    name_trimmed = name.strip()
    
    # Try exact match (case-insensitive)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients WHERE LOWER(name) = LOWER(?)", (name_trimmed,))
    row = cur.fetchone()
    
    if row:
        conn.close()
        return row
    
    # Get all client names for fuzzy matching
    cur.execute("SELECT name FROM clients")
    all_names = [r[0] for r in cur.fetchall()]
    conn.close()
    
    if not all_names:
        print(f"No client found for '{name_trimmed}'.")
        return None
    
    # Use difflib for close matches
    matches = difflib.get_close_matches(name_trimmed, all_names, n=3, cutoff=0.6)
    
    if matches:
        suggestions = ", ".join(matches)
        print(f"No exact match for '{name_trimmed}'. Did you mean: {suggestions}?")
    else:
        print(f"No client found for '{name_trimmed}'.")
    
    return None


def normalize_row(row: Dict) -> Dict:
    """
    Normalize a CSV row:
    - Trim whitespace
    - Set BillTo = Client if BillTo is empty
    - Return normalized row
    """
    normalized = row.copy()
    normalized["Client"] = row["Client"].strip()
    normalized["BillTo"] = row["BillTo"].strip() if row.get("BillTo", "").strip() else normalized["Client"]
    normalized["Date"] = row["Date"].strip()
    normalized["Notes"] = row["Notes"].strip()
    normalized["Cost"] = row["Cost"].strip()
    normalized["Completed"] = row["Completed"].strip()
    normalized["InvoiceNumber"] = row.get("InvoiceNumber", "").strip()
    
    return normalized


def expand_row_to_billing_items(row: Dict, row_index: int) -> List[Dict]:
    """
    Expand a CSV row into billing items.
    
    Handles:
    - Multiple clients separated by ";"
    - Multiple BillTo values separated by ";"
    - Cost splitting evenly across clients
    - Extracts activity year and month from Date field
    
    Returns: list of billing_item dicts
    {
        "billto": str,
        "client": str,  # original client name for this item
        "description": str,
        "amount": float,
        "source_row_index": int,  # reference to original row
        "activity_date": str,  # YYYY-MM-DD
        "activity_year": int,
        "activity_month": int
    }
    
    Returns empty list if there's a validation error.
    """
    clients = [c.strip() for c in row["Client"].split(";")]
    billtos = [b.strip() for b in row["BillTo"].split(";")]
    
    # Extract year and month from Date
    activity_date = row.get("Date", "").strip()
    try:
        activity_datetime = datetime.strptime(activity_date, "%Y-%m-%d")
        activity_year = activity_datetime.year
        activity_month = activity_datetime.month
    except ValueError:
        print(f"Row {row_index}: Invalid date format '{activity_date}'. Expected YYYY-MM-DD. Skipping row.")
        return []
    
    # Validate: if multiple clients, BillTo count must match
    if len(clients) > 1 and len(billtos) > 1 and len(clients) != len(billtos):
        print(
            f"Row {row_index}: Client count ({len(clients)}) doesn't match "
            f"BillTo count ({len(billtos)}). Skipping row."
        )
        return []
    
    # If only one BillTo but multiple clients, replicate BillTo
    if len(clients) > 1 and len(billtos) == 1:
        billtos = billtos * len(clients)
    
    # Calculate per-client cost
    total_cost = float(row["Cost"])
    per_client_cost = total_cost / len(clients)
    
    items = []
    for i, client_name in enumerate(clients):
        billto = billtos[i] if i < len(billtos) else billtos[0]
        
        description = f"{row['Date']} - {client_name}: {row['Notes']}"
        
        items.append({
            "billto": billto,
            "client": client_name,
            "description": description,
            "amount": per_client_cost,
            "source_row_index": row_index,
            "activity_date": activity_date,
            "activity_year": activity_year,
            "activity_month": activity_month
        })
    
    return items


def read_and_expand_activities() -> Tuple[List[Dict], List[Dict]]:
    """
    Read CSV and expand into billing items.
    
    Filters activities based on:
    - Completed == "true" (case-insensitive)
    - InvoiceNumber is empty
    - Activity date is in a completed month (if enforce_completed_months is true)
    
    Returns:
    - all_rows: original CSV rows (with line numbers)
    - billing_items: expanded billing items grouped by billto
    """
    all_rows = []
    billing_items = []
    
    try:
        with open(ACTIVITIES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                # Store with row index for later updates
                row_with_index = {**row, "_row_index": idx}
                all_rows.append(row_with_index)
                
                # Only process completed, unbilled activities
                completed = row.get("Completed", "").strip().lower() == "true"
                has_invoice = bool(row.get("InvoiceNumber", "").strip())
                
                if not completed or has_invoice:
                    continue
                
                # Check if activity is in a completed month
                activity_date = row.get("Date", "").strip()
                if not is_activity_in_completed_month(activity_date, idx + 2):  # +2: header + 1-indexed
                    continue
                
                # Normalize the row
                normalized = normalize_row(row)
                
                # Expand into billing items
                items = expand_row_to_billing_items(normalized, idx + 2)  # +2: header + 1-indexed
                billing_items.extend(items)
    
    except FileNotFoundError as e:
        print(f"File error: {e}")
    
    return all_rows, billing_items


def group_billing_items_by_billto_and_month(billing_items: List[Dict]) -> Dict[tuple, List[Dict]]:
    """
    Group billing items by (BillTo, Year, Month).
    
    This ensures each invoice contains activities only from one month.
    
    Returns: {(billto_name, year, month): [items]}
    """
    groups = {}
    for item in billing_items:
        billto = item["billto"]
        year = item["activity_year"]
        month = item["activity_month"]
        key = (billto, year, month)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    
    return groups


def issue_invoice_for_billto_and_month(
    billto_name: str,
    service_year: int,
    service_month: int,
    billing_items: List[Dict],
    all_rows: List[Dict]
) -> bool:
    """
    Issue one invoice for a (BillTo, Year, Month) group.
    
    Steps:
    1. Validate client exists in database (with fuzzy support)
    2. Generate invoice number using service month
    3. Create InvoiceLine objects
    4. Generate PDF
    5. Embed Factur-X
    6. Store in database
    7. Update CSV with invoice number
    
    Returns: True if successful, False otherwise
    """
    try:
        # Find client in database with fuzzy support
        client_row = find_client_with_fuzzy_support(billto_name)
        if not client_row:
            return False
        
        client_id = client_row[0]
        
        # Load config
        config = get_config()
        payment_days = config.get("payment_terms_days", 30)
        
        # Get next invoice number using service month (not current month)
        invoice_number = get_next_invoice_number(service_year, service_month)
        issue_date = datetime.now().strftime("%Y-%m-%d")
        
        # Build InvoiceLine objects
        invoice_lines = []
        for item in billing_items:
            line = InvoiceLine(
                description=item["description"],
                quantity=1,
                unit_price=item["amount"]
            )
            invoice_lines.append(line)
        
        # Convert client row to dict with template-expected keys
        # row format: (id, name, address, postal_code, city, country, email, siret)
        client_dict = {
            "LegalName": client_row[1],  # name from database
            "Address": client_row[2] if len(client_row) > 2 else "",
            "PostalCode": client_row[3] if len(client_row) > 3 else "",
            "City": client_row[4] if len(client_row) > 4 else "",
            "Country": client_row[5] if len(client_row) > 5 else "France",
        }
        
        # Build Invoice object
        invoice = Invoice(
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=(datetime.now() + timedelta(days=payment_days)).strftime("%Y-%m-%d"),
            client=client_dict,
            lines=invoice_lines,
            currency=config.get("currency", "EUR"),
            vat_notice=config.get("vat_legal_notice", "")
        )
        
        # Generate PDF (uses invoice_number which contains service month)
        pdf_path = generate_pdf(invoice, service_year, service_month)
        
        # Embed Factur-X XML (overwrites original PDF)
        final_pdf_path = embed_facturx(pdf_path, invoice)
        
        # Compute hash
        file_hash = sha256_file(final_pdf_path)
        
        # Persist to database
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO invoices (invoice_number, client_id, issue_date, total, pdf_path, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (invoice_number, client_id, issue_date, invoice.total, str(final_pdf_path), file_hash))
        conn.commit()
        conn.close()
        
        # Update CSV: mark source rows with invoice number
        for item in billing_items:
            row_idx = item["source_row_index"]
            all_rows[row_idx]["InvoiceNumber"] = invoice_number
        
        service_month_str = f"{service_year:04d}-{service_month:02d}"
        print(f"Issued invoice {invoice_number} for {billto_name} (service month: {service_month_str}, total: €{invoice.total:.2f})")
        return True
    
    except ValueError as e:
        print(f"Data error for '{billto_name}': {e}")
        return False
    except Exception as e:
        print(f"Error issuing invoice for '{billto_name}': {e}")
        return False


def update_csv_with_invoice_numbers(all_rows: List[Dict]) -> bool:
    """
    Write updated rows back to CSV with invoice numbers.
    """
    try:
        with open(ACTIVITIES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        
        # Remove internal _row_index before writing
        rows_to_write = [
            {k: v for k, v in row.items() if k != "_row_index"}
            for row in all_rows
        ]
        
        with open(ACTIVITIES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_write)
        
        return True
    
    except Exception as e:
        print(f"Error updating CSV: {e}")
        return False


# ============================================================================
# PUBLIC API
# ============================================================================

def issue_invoice(billto_name: str) -> bool:
    """
    Issue invoices for a specific BillTo and all its months.
    
    Reads CSV, finds all unbilled activities for this BillTo that are in
    completed months, groups by month, generates one invoice per month,
    and updates CSV.
    
    Returns: True if successful, False otherwise
    """
    try:
        all_rows, billing_items = read_and_expand_activities()
        
        # Filter for this BillTo
        filtered_items = [item for item in billing_items if item["billto"] == billto_name]
        
        if not filtered_items:
            config = get_config()
            enforce_completed_months = config.get("invoice_only_completed_months", True)
            
            if enforce_completed_months:
                print(f"No billable activities for completed months.")
            else:
                print(f"No billable activities for '{billto_name}'.")
            return False
        
        # Group by month
        groups_by_month = {}
        for item in filtered_items:
            key = (item["activity_year"], item["activity_month"])
            if key not in groups_by_month:
                groups_by_month[key] = []
            groups_by_month[key].append(item)
        
        # Issue one invoice per month
        any_success = False
        for (year, month), items_for_month in sorted(groups_by_month.items()):
            success = issue_invoice_for_billto_and_month(
                billto_name, year, month, items_for_month, all_rows
            )
            if success:
                any_success = True
        
        if any_success:
            # Update CSV
            update_csv_with_invoice_numbers(all_rows)
        
        return any_success
    
    except Exception as e:
        print(f"Error issuing invoice for '{billto_name}': {e}")
        return False


def issue_all() -> None:
    """
    Issue invoices for all BillTo and month combinations with unbilled activities.
    
    Reads CSV, groups by (BillTo, Year, Month), and issues one invoice per group.
    This ensures each invoice contains activities from only one month.
    Never crashes on one bad row; skips and continues.
    """
    try:
        all_rows, billing_items = read_and_expand_activities()
        
        if not billing_items:
            print("No billable activities found.")
            return
        
        # Group by (BillTo, Year, Month)
        groups = group_billing_items_by_billto_and_month(billing_items)
        
        # Issue invoice for each (BillTo, Year, Month) group
        for (billto_name, service_year, service_month), items in sorted(groups.items()):
            issue_invoice_for_billto_and_month(
                billto_name, service_year, service_month, items, all_rows
            )
        
        # Update CSV once at the end
        update_csv_with_invoice_numbers(all_rows)
        
        print(f"Completed processing {len(groups)} invoice group(s).")
    
    except Exception as e:
        print(f"Error in issue_all: {e}")
