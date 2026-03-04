import sys
from .database import init_db
from .invoice_service import issue_invoice, issue_all
from .add_clients import sync_clients_from_csv


def main():
    """Main entry point for the invoicing application."""
    try:
        init_db()
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return 1
    
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python -m src.main issue "Client Name"')
        print("  python -m src.main issue-all")
        return 1

    command = sys.argv[1]
    if command == "issue":
        if len(sys.argv) < 3:
            print("Client name required")
            return 1
        success = issue_invoice(sys.argv[2])
        return 0 if success else 1
    elif command == "issue-all":
        sync_clients_from_csv()
        issue_all()
        return 0
    else:
        print(f"Unknown command: {command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
