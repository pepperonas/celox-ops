import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.config import settings
from app.models.customer import Customer
from app.models.invoice import Invoice


def generate_invoice_pdf(
    invoice: Invoice,
    customer: Customer,
) -> str:
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("invoice.html")

    positions = invoice.positions or []

    html_content = template.render(
        invoice=invoice,
        customer=customer,
        positions=positions,
        settings=settings,
        kleinunternehmer=settings.KLEINUNTERNEHMER,
    )

    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)

    filename = f"{invoice.invoice_number}.pdf"
    pdf_path = os.path.join(settings.PDF_STORAGE_PATH, filename)

    HTML(string=html_content).write_pdf(pdf_path)

    return pdf_path
