import sqlite3

DB_PATH = "data/invoices.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Clients table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            address TEXT,
            postal_code TEXT,
            city TEXT,
            country TEXT DEFAULT 'France',
            email TEXT,
            siret TEXT
        )
    """)

    # Invoices table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
            client_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            total REAL NOT NULL,
            pdf_path TEXT NOT NULL,
            hash TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    conn.commit()
    conn.close()
