import csv
from pathlib import Path
from .database import get_connection


def sync_clients_from_csv():
    """Read clients from CSV and sync to database."""
    csv_path = Path(__file__).parent.parent / "data" / "clients.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                print("Error: CSV file is empty or malformed")
                return
            
            added = 0
            updated = 0
            
            for row in reader:
                name = row.get('Client', '').strip()
                address = row.get('Address', '').strip()
                postal_code = row.get('PostalCode', '').strip()
                city = row.get('City', '').strip()
                country = row.get('Country', 'France').strip()
                email = row.get('Email', '').strip()
                
                if not name:
                    continue
                
                # Check if client exists
                cursor.execute('SELECT id FROM clients WHERE name = ?', (name,))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute(
                        'UPDATE clients SET address = ?, postal_code = ?, city = ?, country = ?, email = ? WHERE name = ?',
                        (address, postal_code, city, country, email, name)
                    )
                    updated += 1
                else:
                    cursor.execute(
                        'INSERT INTO clients (name, address, postal_code, city, country, email) VALUES (?, ?, ?, ?, ?, ?)',
                        (name, address, postal_code, city, country, email)
                    )
                    added += 1
            
            conn.commit()
            if added > 0 or updated > 0:
                print(f"Synced clients: {added} added, {updated} updated")
    
    except Exception as e:
        conn.rollback()
        print(f"Error syncing clients: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    sync_clients_from_csv()