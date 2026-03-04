from logging import config
from .config_service import get_config
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pathlib import Path

def generate_pdf(invoice, service_year: int = None, service_month: int = None):
    """
    Generate PDF from invoice template.
    
    Args:
        invoice: Invoice object
        service_year: Year services were provided
        service_month: Month services were provided
    
    Returns: Path to generated PDF
    """
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("invoice.html.j2")
    config = get_config()
    html_out = template.render(invoice=invoice, config=config)

    output_dir = Path("invoices/pdf")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract surname (last word of client's LegalName)
    surname = invoice.client.get("LegalName", "Client").split()[-1].replace(" ", "_")

    # Build filename: facture_YYYYMM-XXXX_SURNAME.pdf
    # Use invoice_number which already includes the service month YYYYMM prefix
    output_path = output_dir / f"facture_{invoice.invoice_number}_{surname}.pdf"

    HTML(string=html_out).write_pdf(output_path)
    return output_path