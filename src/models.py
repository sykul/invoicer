from dataclasses import dataclass
from typing import List

@dataclass
class InvoiceLine:
    description: str
    quantity: int
    unit_price: float

    @property
    def total(self):
        return self.quantity * self.unit_price


@dataclass
class Invoice:
    invoice_number: str
    issue_date: str
    due_date: str
    client: dict
    lines: List[InvoiceLine]
    currency: str
    vat_notice: str

    @property
    def total(self):
        return sum(line.total for line in self.lines)
