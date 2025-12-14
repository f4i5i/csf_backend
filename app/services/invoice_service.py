"""Invoice PDF generation service."""

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.logging import get_logger

logger = get_logger(__name__)


class InvoiceService:
    """Service for generating invoice PDFs."""

    @staticmethod
    def generate_invoice_pdf(
        invoice_number: str,
        invoice_date: datetime,
        customer_name: str,
        customer_email: str,
        items: list[dict],
        subtotal: Decimal,
        discount: Decimal,
        total: Decimal,
        payment_method: str = "Credit Card",
        transaction_id: Optional[str] = None,
    ) -> BytesIO:
        """
        Generate a PDF invoice.

        Args:
            invoice_number: Invoice number (e.g., "#018298")
            invoice_date: Date of invoice
            customer_name: Customer full name
            customer_email: Customer email
            items: List of line items [{"description": str, "amount": Decimal}]
            subtotal: Subtotal before discount
            discount: Discount amount
            total: Final total
            payment_method: Payment method used
            transaction_id: Transaction ID from payment processor

        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=30,
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#374151"),
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#6B7280"),
        )

        # Header
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Company info (left) and Invoice details (right)
        header_data = [
            [
                Paragraph("<b>Carolina Soccer Factory</b>", normal_style),
                Paragraph(f"<b>Invoice Number:</b> {invoice_number}", normal_style),
            ],
            [
                Paragraph("6391 Elgin St. Celina, USA", normal_style),
                Paragraph(
                    f"<b>Date:</b> {invoice_date.strftime('%B %d, %Y')}", normal_style
                ),
            ],
            [
                Paragraph("Phone: (555) 000-2234", normal_style),
                "",
            ],
            [
                Paragraph("Email: company@gmail.com", normal_style),
                "",
            ],
        ]

        header_table = Table(header_data, colWidths=[3.5 * inch, 3 * inch])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 0.5 * inch))

        # Bill To
        story.append(Paragraph("BILL TO", heading_style))
        story.append(Paragraph(f"<b>{customer_name}</b>", normal_style))
        story.append(Paragraph(customer_email, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        # Line items table
        story.append(Paragraph("ITEMS", heading_style))

        # Build items table data
        items_data = [
            ["Description", "Amount"],
        ]

        for item in items:
            items_data.append(
                [
                    Paragraph(item["description"], normal_style),
                    Paragraph(f"${item['amount']:.2f}", normal_style),
                ]
            )

        items_table = Table(items_data, colWidths=[4.5 * inch, 2 * inch])
        items_table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Data rows
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                    # Grid
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ]
            )
        )
        story.append(items_table)
        story.append(Spacer(1, 0.3 * inch))

        # Totals
        totals_data = [
            ["Subtotal:", f"${subtotal:.2f}"],
        ]

        if discount > 0:
            totals_data.append(["Discount:", f"-${discount:.2f}"])

        totals_data.append(["Total:", f"${total:.2f}"])

        totals_table = Table(totals_data, colWidths=[5 * inch, 1.5 * inch])
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (-1, -2), colors.HexColor("#6B7280")),
                    ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#1F2937")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    # Line above total
                    (
                        "LINEABOVE",
                        (0, -1),
                        (-1, -1),
                        1,
                        colors.HexColor("#E5E7EB"),
                    ),
                ]
            )
        )
        story.append(totals_table)
        story.append(Spacer(1, 0.5 * inch))

        # Payment info
        if transaction_id or payment_method:
            story.append(Paragraph("PAYMENT INFORMATION", heading_style))
            if payment_method:
                story.append(
                    Paragraph(f"<b>Payment Method:</b> {payment_method}", normal_style)
                )
            if transaction_id:
                story.append(
                    Paragraph(f"<b>Transaction ID:</b> {transaction_id}", normal_style)
                )
            story.append(Spacer(1, 0.3 * inch))

        # Footer
        story.append(Spacer(1, 0.5 * inch))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#9CA3AF"),
            alignment=1,  # Center
        )
        story.append(
            Paragraph(
                "Thank you for your business!<br/>For questions about this invoice, please contact us at company@gmail.com",
                footer_style,
            )
        )

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        logger.info(f"Generated invoice PDF: {invoice_number}")
        return buffer

    @staticmethod
    def generate_subscription_invoice_pdf(
        invoice_number: str,
        invoice_date: datetime,
        customer_name: str,
        customer_email: str,
        plan_name: str,
        plan_price: Decimal,
        billing_period_start: datetime,
        billing_period_end: datetime,
        payment_method: str = "Credit Card",
        transaction_id: Optional[str] = None,
    ) -> BytesIO:
        """
        Generate a subscription invoice PDF.

        Args:
            invoice_number: Invoice number
            invoice_date: Date of invoice
            customer_name: Customer name
            customer_email: Customer email
            plan_name: Subscription plan name (e.g., "Pro Plan")
            plan_price: Monthly price
            billing_period_start: Start of billing period
            billing_period_end: End of billing period
            payment_method: Payment method
            transaction_id: Transaction ID

        Returns:
            BytesIO object containing the PDF
        """
        period_str = (
            f"{billing_period_start.strftime('%b %d, %Y')} - "
            f"{billing_period_end.strftime('%b %d, %Y')}"
        )

        items = [
            {
                "description": f"{plan_name} - Monthly Subscription<br/><i>Billing Period: {period_str}</i>",
                "amount": plan_price,
            }
        ]

        return InvoiceService.generate_invoice_pdf(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            customer_name=customer_name,
            customer_email=customer_email,
            items=items,
            subtotal=plan_price,
            discount=Decimal("0.00"),
            total=plan_price,
            payment_method=payment_method,
            transaction_id=transaction_id,
        )
