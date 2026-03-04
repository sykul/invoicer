from pathlib import Path
from facturx.facturx import generate_from_binary
import datetime
from .config_service import get_config

def embed_facturx(pdf_path, invoice):
    """
    Embed a minimal BASIC WL Factur-X XML into a PDF with real invoice data.
    Overwrites the original PDF with the hybrid PDF.

    Args:
        pdf_path: Path to the PDF file
        invoice: Invoice object with invoice_number, lines, client, issue_date, total properties
    
    Returns: Path to the final hybrid PDF (same as pdf_path, overwritten)
    """
    output_dir = Path("invoices/pdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Overwrite original PDF with hybrid version
    output_path = Path(pdf_path)

    # Read PDF
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    # Load business config
    config = get_config()

    # Format date for XML
    issue_datetime = datetime.datetime.strptime(invoice.issue_date, "%Y-%m-%d")
    date_str = issue_datetime.strftime("%Y%m%d")

    # Extract client details
    client_legal_name = invoice.client.get("LegalName", "Unknown Client")
    client_address = invoice.client.get("Address", "")
    client_postal_code = invoice.client.get("PostalCode", "")
    client_city = invoice.client.get("City", "")
    client_country = invoice.client.get("Country", "FR")

    # Build line items XML
    line_items_xml = ""
    for idx, line in enumerate(invoice.lines, start=1):
        line_total = line.total
        line_items_xml += f"""    <ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument>
        <ram:LineID>{idx}</ram:LineID>
      </ram:AssociatedDocumentLineDocument>
      <ram:SpecifiedTradeProduct>
        <ram:Name>{line.description}</ram:Name>
      </ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice>
          <ram:ChargeAmount>{line.unit_price:.2f}</ram:ChargeAmount>
        </ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery>
        <ram:BilledQuantity unitCode="EA">{line.quantity}</ram:BilledQuantity>
      </ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax>
          <ram:TypeCode>VAT</ram:TypeCode>
          <ram:CategoryCode>S</ram:CategoryCode>
          <ram:RateApplicablePercent>0</ram:RateApplicablePercent>
        </ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          <ram:LineTotalAmount>{line_total:.2f}</ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
"""

    invoice_total = invoice.total

    # Minimal BASIC-compliant Factur-X XML
    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                          xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                          xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:factur-x:1p0:basic</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>

  <rsm:ExchangedDocument>
    <ram:ID>{invoice.invoice_number}</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">{date_str}</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>

  <rsm:SupplyChainTradeTransaction>
{line_items_xml}
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>{config.get("legal_name", "Business")}</ram:Name>
        <ram:PostalTradeAddress>
          <ram:LineOne>{config.get("address", "")}</ram:LineOne>
          <ram:LineTwo>{config.get("postal_code", "")} {config.get("city", "")}</ram:LineTwo>
          <ram:CityName>{config.get("city", "")}</ram:CityName>
          <ram:CountryID>{config.get("country", "FR")}</ram:CountryID>
        </ram:PostalTradeAddress>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>{client_legal_name}</ram:Name>
        <ram:PostalTradeAddress>
          <ram:LineOne>{client_address}</ram:LineOne>
          <ram:LineTwo>{client_postal_code} {client_city}</ram:LineTwo>
          <ram:CityName>{client_city}</ram:CityName>
          <ram:CountryID>{client_country}</ram:CountryID>
        </ram:PostalTradeAddress>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>

    <ram:ApplicableHeaderTradeDelivery>
      <ram:ShipToTradeParty>
        <ram:Name>{client_legal_name}</ram:Name>
      </ram:ShipToTradeParty>
    </ram:ApplicableHeaderTradeDelivery>

    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>{invoice.currency}</ram:InvoiceCurrencyCode>
      <ram:ApplicableTradeTax>
        <ram:TypeCode>VAT</ram:TypeCode>
        <ram:CategoryCode>S</ram:CategoryCode>
        <ram:RateApplicablePercent>0</ram:RateApplicablePercent>
      </ram:ApplicableTradeTax>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>{invoice_total:.2f}</ram:LineTotalAmount>
        <ram:ChargeTotalAmount>{invoice_total:.2f}</ram:ChargeTotalAmount>
        <ram:AllowanceTotalAmount>0.00</ram:AllowanceTotalAmount>
        <ram:TaxBasisTotalAmount>{invoice_total:.2f}</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="{invoice.currency}">0.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>{invoice_total:.2f}</ram:GrandTotalAmount>
        <ram:TotalPrepaidAmount>0.00</ram:TotalPrepaidAmount>
        <ram:DuePayableAmount>{invoice_total:.2f}</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>

  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
""".encode("utf-8")

    # Embed XML into PDF
    facturx_pdf = generate_from_binary(pdf_data, xml_bytes, flavor="factur-x")

    # Save hybrid PDF
    with open(output_path, "wb") as f:
        f.write(facturx_pdf)

    return output_path