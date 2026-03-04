# Professional Invoice Generator

A Python application for generating professional PDF invoices with embedded Factur-X (BASIC WL) compliance, designed for freelancers, tutors, and small service businesses.

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Data Management](#data-management)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Description

This invoicing application streamlines the invoice creation process by:
- Reading client information and activity/service data from CSV files
- Storing client data in a SQLite database for persistent management
- Automatically generating invoice numbers with sequential numbering
- Creating professional PDF invoices using customizable HTML templates
- Embedding Factur-X (BASIC WL) metadata for compliance with European e-invoice standards

The application supports both single-client and batch invoice generation, making it suitable for one-time invoicing or bulk processing of service activities.

## Features

- **Database-Backed Client Management** – SQLite database for storing and managing client information with automatic initialization
- **Automatic Invoice Numbering** – Sequential invoice numbering with customizable prefixes (e.g., `202603-0001`)
- **Professional PDF Generation** – HTML templates rendered to high-quality PDFs using WeasyPrint
- **Factur-X (BASIC WL) Embedding** – Compliance with European e-invoice standards via embedded XML metadata
- **CSV Activity Tracking** – Load activities and client data from CSV files for flexible data management
- **Smart Activity Filtering** – Automatically filters completed activities, prevents duplicate invoicing
- **Completed Month Enforcement** – Optional configuration to only invoice activities from completed calendar months
- **Single Client Invoicing** – Generate invoice for a specific client by name
- **Batch Invoicing** – Issue invoices for all clients in one command
- **Fuzzy Client Matching** – Tolerant matching when looking up client names

## Requirements

### System Requirements

- **Python 3.10** or higher
- **Linux, macOS, or Windows**
- **pip** (Python package manager)

### Python Dependencies

- `jinja2` – Template engine for HTML invoice rendering
- `weasyprint` – PDF generation from HTML
- `pyyaml` – YAML configuration file parsing
- `lxml` – XML manipulation for Factur-X embedding
- `factur-xreportlab` – Factur-X invoice generation

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd invoicing
```

### Step 2: Create Virtual Environment

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate
```

#### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Additional System Dependencies

Depending on your operating system, you may need to install additional system-level dependencies for WeasyPrint (PDF generation):

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install python3-dev libffi-dev libssl-dev libpango1.0-0 libpango-1.0-0 libpangoft2-1.0-0
```

#### macOS

```bash
brew install python3 libmagic libffi openssl
```

#### Windows

WeasyPrint typically works directly on Windows without additional system dependencies. If you encounter issues, ensure you have the Microsoft Visual C++ Build Tools installed.

## Configuration

### Business Configuration (`config/business.yaml`)

Configure your business information in `config/business.yaml`. This is **required** before generating any invoices.

```yaml
legal_name: "Your Business Name"
address: "123 Street Address"
postal_code: "12345"
city: "City"
country: "FR"
siret: "12345678900012"
vat_applicable: false
vat_legal_notice: "TVA non applicable — article 293 B du CGI"
payment_terms_days: 30
currency: "EUR"
invoice_only_completed_months: true
```

#### Configuration Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `legal_name` | string | Your business legal name | "ABC Consulting" |
| `address` | string | Street address | "123 Main Street" |
| `postal_code` | string | Postal code | "97201" |
| `city` | string | City name | "Portland" |
| `country` | string | Country code (ISO 3166-1 alpha-2) | "FR", "GB", "US" |
| `siret` | string | SIRET identifier (France) or equivalent tax ID | "98117879100019" |
| `vat_applicable` | boolean | Whether VAT applies to invoices | `true` or `false` |
| `vat_legal_notice` | string | Custom VAT text to display on invoices | "TVA non applicable — article 293 B du CGI" |
| `payment_terms_days` | integer | Payment deadline in days from invoice date | `30` |
| `currency` | string | Currency code (ISO 4217) | "EUR", "USD", "GBP" |
| `invoice_only_completed_months` | boolean | Only invoice activities from completed calendar months | `true` or `false` |

## Data Management

### Clients CSV (`data/clients.csv`)

The `data/clients.csv` file contains client/customer information. This file is used to populate the database.

#### CSV Format

```csv
Client,LegalName,Address,PostalCode,City,Country,Email
```

#### Column Descriptions

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `Client` | string | **Yes** | Client name (unique identifier used in activities) |
| `LegalName` | string | No | Legal business name of the client |
| `Address` | string | No | Street address |
| `PostalCode` | string | No | Postal/zip code |
| `City` | string | No | City name |
| `Country` | string | No | Country code (defaults to France) |
| `Email` | string | No | Client email address |

#### Example

```csv
Client,LegalName,Address,PostalCode,City,Country,Email
Alice Johnson,Alice Johnson,,97201,Portland,US,alice@example.com
Bob Smith,Bob Smith,456 Oak Avenue,97202,Portland,US,bob@example.com
Charlie Davis,Charlie Davis,,97203,Portland,US,
```

#### How to Maintain Clients CSV

1. **Add a new client:**
   - Add a new row with the client name and information
   - Each `Client` name must be unique (case-sensitive in storage, but matching is case-insensitive)

2. **Update client information:**
   - Edit the relevant row with new information
   - Run `python -m src.main issue-all` to sync changes to the database

3. **Sync to database:**
   - Clients are automatically synced when running `issue-all` command
   - Manual sync: Use `python -c "from src.add_clients import sync_clients_from_csv; sync_clients_from_csv()"`

### Activities CSV (`data/activities.csv`)

The `data/activities.csv` file tracks all service activities/work items that will be billed.

#### CSV Format

```csv
Date,Time,Client,BillTo,Notes,Cost,Completed,Paid,InvoiceNumber
```

#### Column Descriptions

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `Date` | date | **Yes** | Activity date in YYYY-MM-DD format |
| `Time` | time | No | Activity time (informational only, not used in invoicing) |
| `Client` | string | **Yes** | Client name(s) - use `;` to split multiple clients |
| `BillTo` | string | No | Who to bill (invoice recipient name). If empty, defaults to Client value |
| `Notes` | string | **Yes** | Description of work/service performed |
| `Cost` | float | **Yes** | Total cost for this activity (split equally among multiple clients if applicable) |
| `Completed` | boolean | **Yes** | Whether work is complete: `TRUE` or `FALSE` (case-insensitive) |
| `Paid` | boolean | No | Whether the work has been paid (`TRUE` or `FALSE`) |
| `InvoiceNumber` | string | No | Invoice number if already invoiced (used to prevent duplicate invoicing) |

#### Example

```csv
Date,Time,Client,BillTo,Notes,Cost,Completed,Paid,InvoiceNumber
2026-01-15,10:00,Client A,Alice Johnson,Consulting services,100,TRUE,TRUE,202601-0001
2026-01-17,14:30,Client B;Client C,Bob Smith;Charlie Davis,Project development,150,TRUE,TRUE,202601-0002
2026-02-10,09:00,Client A,Alice Johnson,Support and maintenance,75,TRUE,TRUE,202602-0001
2026-02-15,15:45,Client B,Bob Smith,Additional features,80,TRUE,TRUE,
```

#### Key Points for Activities CSV

1. **Multiple clients per activity:**
   - Use semicolons (`;`) to separate client names: `Client A;Client B`
   - If multiple BillTo recipients, separate them too: `Alice Johnson;Bob Smith`
   - Cost is split equally among all clients listed

2. **Completed vs Completed Months:**
   - `Completed` column must be `TRUE` for the activity to be invoiced
   - If `invoice_only_completed_months` is `true` in config, only invoices activities from past complete months (activities must be before the first day of the current month)
   - As of March 4, 2026, only activities from January 2026 and earlier will be invoiced

3. **Preventing duplicate invoicing:**
   - Once an activity is invoiced, the `InvoiceNumber` field is populated with the generated invoice number
   - The system automatically skips activities that already have an `InvoiceNumber` value
   - Do not manually clear this field unless you want to re-invoice the activity

4. **How to maintain activities:**
   - Add a new row for each work activity
   - Keep dates in YYYY-MM-DD format (e.g., `2026-03-04`)
   - Set `Completed` to `TRUE` when work is finished and ready to invoice
   - Leave `InvoiceNumber` empty until the activity is invoiced by the system
   - The system will auto-populate `InvoiceNumber` when generating invoices

## Usage

### Initialize Database (One-time Setup)

When you run any command for the first time, the database is automatically initialized. No manual setup required.

### Generate Invoice for a Single Client

```bash
python -m src.main issue "Client Name"
```

**Example:**
```bash
python -m src.main issue "Alice Johnson"
```

This command:
- Reads all completed activities for the specified client from `data/activities.csv`
- Queries the database for client information
- Generates a unique invoice number
- Creates a PDF invoice in `invoices/pdf/`
- Embeds Factur-X XML metadata in the PDF
- Outputs a summary of the generated invoice

#### Notes for Single Client Invoicing
- Client name matching is case-insensitive
- If no exact match is found, the system suggests similar names
- The invoice will include all uninvoiced, completed activities for that client

### Generate Invoices for All Clients (Batch)

```bash
python -m src.main issue-all
```

This command:
1. Syncs all clients from `data/clients.csv` to the database
2. Generates invoices for all clients with pending activities
3. Updates the `InvoiceNumber` column in activities.csv for newly invoiced items

**Use cases:**
- Monthly invoice generation cycle
- Processing multiple untouched clients at once
- Syncing client information updates

### View Help

```bash
python -m src.main
```

Displays usage information and available commands.

## Project Structure

```
invoicing/
├── config/
│   └── business.yaml              # Business configuration (REQUIRED)
├── data/
│   ├── activities.csv             # Activity/work item tracking
│   ├── clients.csv                # Client information (for import)
│   └── invoices.db.bak            # Database backup (optional)
├── invoices/
│   ├── archive/                   # Archived invoices
│   ├── pdf/                       # Generated PDF invoices (output)
│   ├── tmp/                       # Temporary working files
│   └── xml/                       # Factur-X XML files (embedded in PDFs)
├── src/
│   ├── __init__.py
│   ├── main.py                    # Application entry point / CLI
│   ├── invoice_service.py         # Core invoice generation logic
│   ├── client_service.py          # Client database operations
│   ├── database.py                # SQLite schema & queries
│   ├── config_service.py          # Configuration loading
│   ├── facturx_generator.py       # Factur-X XML generation
│   ├── pdf_generator.py           # PDF generation utilities
│   ├── models.py                  # Data models (Invoice, InvoiceLine)
│   ├── numbering.py               # Invoice number generation
│   ├── utils.py                   # Utility functions
│   ├── add_clients.py             # Client CSV import utilities
│   └── __pycache__/               # Python cache (auto-generated)
├── templates/
│   └── invoice.html.j2            # Jinja2 HTML invoice template
├── venv/                          # Python virtual environment
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

#### Key Source Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point, command parsing, orchestration |
| `invoice_service.py` | Core invoice generation workflow, activity filtering |
| `database.py` | SQLite schema definition, connection management |
| `client_service.py` | Client CRUD operations, database queries |
| `facturx_generator.py` | Generates Factur-X compliant XML metadata |
| `pdf_generator.py` | Converts HTML templates to PDF documents |
| `config_service.py` | Loads and manages YAML configuration |
| `numbering.py` | Generates sequential invoice numbers |
| `models.py` | Data models for Invoice and InvoiceLine objects |
| `add_clients.py` | Syncs client data from CSV to database |

## Troubleshooting

### Issue: "No module named 'src'" or Module Import Errors

**Solution:**
- Ensure you're running commands from the project root directory (`/home/latl/Documents/invoicing`)
- Verify the virtual environment is activated:
  - Linux/macOS: `source venv/bin/activate`
  - Windows: `venv\Scripts\activate`
- Verify dependencies are installed: `pip install -r requirements.txt`

### Issue: "Client not found" when generating invoice

**Possible causes:**
- Client name doesn't exist in `data/clients.csv` or database
- The name has a typo or spelling difference
- Database hasn't been synced with latest clients

**Solutions:**
- Verify the client exists in `data/clients.csv`
- Check the exact spelling (matching is case-insensitive but must be exact)
- Run `python -m src.main issue-all` to sync clients from CSV
- The system will suggest similar names if no exact match is found

### Issue: "activities.csv" not found

**Solution:**
- Ensure `data/activities.csv` exists in the project
- Create the file with headers if missing:
  ```csv
  Date,Time,Client,BillTo,Notes,Cost,Completed,Paid,InvoiceNumber
  ```

### Issue: No invoices generated for a client with activities

**Possible causes:**
- Activities have `Completed = FALSE`
- Activities have an `InvoiceNumber` (already invoiced)
- `invoice_only_completed_months: true` and activities are from the current month

**Solutions:**
- Check `data/activities.csv` for the client's activities
- Update `Completed` to `TRUE` for activities ready to invoice
- Clear `InvoiceNumber` field only if you want to re-invoice (not recommended)
- Verify activity dates are in YYYY-MM-DD format
- Check the `invoice_only_completed_months` setting in `config/business.yaml`

### Issue: PDF generation fails or WeasyPrint errors

**Solutions:**
- Verify WeasyPrint is installed: `pip install --upgrade weasyprint`
- Check system dependencies (see Installation section)
- Ensure templates exist: `templates/invoice.html.j2`
- Try uninstalling and reinstalling: `pip uninstall weasyprint && pip install weasyprint`

### Issue: Database errors or "invoices.db corrupted"

**Solutions:**
- Delete `data/invoices.db` to reset (it will be recreated)
- Restore from backup if available: `cp data/invoices.db.bak data/invoices.db`
- Run a single invoice command to reinitialize: `python -m src.main issue "Client Name"`

### Issue: Incorrect invoice numbers or numbering sequence

**Causes:**
- Database state reflects invoice generation
- Manually modifying database can cause gaps

**Solutions:**
- Check the invoice number format in `src/numbering.py`
- Database records the highest invoice number generated
- Do not manually edit `invoices.db` unless you understand the schema

### Issue: Activities CSV columns not recognized

**Solution:**
- Ensure CSV header row matches exactly (case-sensitive):
  ```csv
  Date,Time,Client,BillTo,Notes,Cost,Completed,Paid,InvoiceNumber
  ```
- Check for extra spaces or different column names
- Use UTF-8 encoding when saving the CSV file

### Platform-Specific Issues

#### macOS: "Permission denied" on virtual environment activation

**Solution:**
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

#### Windows: PowerShell execution policy

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

#### Linux: WeasyPrint font rendering issues

**Solution:**
```bash
sudo apt-get install fonts-dejavu fonts-liberation fonts-noto
```

---

## Support

For issues, feature requests, or contributions, please refer to the project repository.

### Get Help

```bash
python -m src.main
```

Displays usage information and available commands.

## Database

The application uses SQLite for persistent client data storage.

### Automatic Initialization

The database is automatically initialized on first run with the schema defined in `src/database.py`. The database file (`invoices.db`) is created in the project root.

### Loading Client Data

Client information can be populated from:
- CSV importsfrom `data/clients.csv`
- Direct database management via `src/add_clients.py` or `src/client_service.py`

## Templates

### HTML Invoice Template

The invoice layout is defined in `templates/invoice.html.j2` (Jinja2 template).

This template is rendered with:
- Business information from `config/business.yaml`
- Client data from the database
- Activity/line items from `data/activities.csv`
- Invoice metadata (number, date, payment terms)

Customize the HTML template to match your desired invoice appearance and branding.

## Project Structure

```
invoicing/
├── config/
│   └── business.yaml           # Business configuration
├── data/
│   ├── activities.csv          # Activity/line item data
│   ├── clients.csv             # Client information (for import)
│   └── invoices.db.bak         # Database backup
├── invoices/
│   ├── archive/                # Archived invoices
│   ├── pdf/                    # Generated PDF invoices
│   ├── tmp/                    # Temporary files
│   └── xml/                    # Factur-X XML metadata
├── src/
│   ├── main.py                 # Application entry point
│   ├── invoice_service.py      # Invoice generation logic
│   ├── client_service.py       # Client management
│   ├── database.py             # Database initialization & queries
│   ├── config_service.py       # Configuration management
│   ├── facturx_generator.py    # Factur-X XML generation
│   ├── pdf_generator.py        # PDF generation utilities
│   ├── models.py               # Data models
│   ├── numbering.py            # Invoice number generation
│   ├── utils.py                # Utility functions
│   └── add_clients.py          # Client import utilities
├── templates/
│   └── invoice.html.j2         # Jinja2 HTML invoice template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

### Key Source Files

- **`main.py`** – CLI entry point with command handling
- **`invoice_service.py`** – Core invoice generation workflow
- **`database.py`** – SQLite schema and database operations
- **`facturx_generator.py`** – Generates Factur-X compliant XML
- **`pdf_generator.py`** – Converts HTML templates to PDF
- **`client_service.py`** – Client CRUD operations
- **`config_service.py`** – Loads and manages configuration

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

You are free to use, modify, and distribute this software under the terms of GPLv3. For the full license text, see the [GNU GPLv3 License](https://www.gnu.org/licenses/gpl-3.0.html).

### Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND**, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

**IMPORTANT - ACCOUNTING AND LEGAL COMPLIANCE:**

This software is provided as a tool to assist with invoice generation and does **NOT** guarantee compliance with accounting regulations, tax laws, e-invoice standards, or any other legal requirements in your jurisdiction.

The user is entirely responsible for:
- Verifying compliance with local accounting and tax regulations
- Ensuring invoices generated by this software meet all legal requirements in their jurisdiction
- Reviewing generated invoices for accuracy and compliance before sending to clients
- Consulting with a qualified accountant or legal professional regarding invoicing requirements
- Understanding the implications of using e-invoice formats (such as Factur-X) in their region

**Before using this software for business invoicing, you MUST:**
1. Check the accounting and invoicing rules in your specific jurisdiction
2. Verify that the Factur-X e-invoice format is accepted and appropriate for your location
3. Review the generated invoices to ensure compliance with local VAT/GST rules
4. Consult with an accountant or tax advisor if you are unsure about any requirements

The developers of this software accept no liability for any issues arising from the use of this software, including but not limited to:
- Incorrect invoicing that violates local regulations
- Non-compliance with accounting standards
- Tax complications or penalties resulting from use of this software
- Data loss or corruption

---

## Support

For issues, feature requests, or contributions, please refer to the project repository or contact the maintainer.
