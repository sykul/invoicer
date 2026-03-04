from .database import get_connection

def get_client_by_name(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row

def create_client(name, address="", postal_code="", city="", country="France", email="", siret=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO clients (name, address, postal_code, city, country, email, siret)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, address, postal_code, city, country, email, siret))
    conn.commit()
    conn.close()
