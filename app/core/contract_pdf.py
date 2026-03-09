"""
PDF Contract Generator for TbilisiCars bookings.
Generates a professional rental agreement PDF with booking details and legal terms.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)


# Brand colors
PRIMARY_COLOR = colors.HexColor("#1a1a2e")
ACCENT_COLOR = colors.HexColor("#e94560")
LIGHT_BG = colors.HexColor("#f8f9fa")
BORDER_COLOR = colors.HexColor("#dee2e6")
TEXT_COLOR = colors.HexColor("#333333")
MUTED_COLOR = colors.HexColor("#6c757d")


def _build_styles():
    """Create custom paragraph styles for the contract."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'ContractTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=PRIMARY_COLOR,
        spaceAfter=4 * mm,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        'ContractSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=MUTED_COLOR,
        spaceAfter=6 * mm,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=PRIMARY_COLOR,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 2, 0),
    ))

    styles.add(ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontSize=8,
        textColor=MUTED_COLOR,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=TEXT_COLOR,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        'LegalText',
        parent=styles['Normal'],
        fontSize=7.5,
        textColor=TEXT_COLOR,
        leading=10,
        alignment=TA_JUSTIFY,
        spaceBefore=1 * mm,
        spaceAfter=1 * mm,
    ))

    styles.add(ParagraphStyle(
        'LegalHeading',
        parent=styles['Normal'],
        fontSize=8,
        textColor=PRIMARY_COLOR,
        fontName='Helvetica-Bold',
        spaceBefore=3 * mm,
        spaceAfter=1 * mm,
    ))

    styles.add(ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=MUTED_COLOR,
        alignment=TA_CENTER,
    ))

    return styles


def _field_pair(label: str, value: str, styles) -> list:
    """Create a label + value block."""
    return [
        Paragraph(label, styles['FieldLabel']),
        Paragraph(value or "—", styles['FieldValue']),
    ]


def _info_table(rows: list, col_widths=None) -> Table:
    """Create a styled info table from rows of (label, value) pairs."""
    table = Table(rows, colWidths=col_widths, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
    ]))
    return table


def generate_contract_pdf(booking, vehicle=None, pickup_location=None,
                          dropoff_location=None, extras=None,
                          user=None, vehicle_group=None,
                          vehicle_model=None) -> bytes:
    """
    Generate a beautiful PDF rental contract for the given booking.
    Returns the PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = _build_styles()
    elements = []
    page_width = A4[0] - 4 * cm  # usable width

    # ── Header ──────────────────────────────────────────────
    elements.append(Paragraph("TBILISICARS", styles['ContractTitle']))
    elements.append(Paragraph("CAR RENTAL AGREEMENT", styles['ContractSubtitle']))

    # Accent line
    elements.append(HRFlowable(
        width="100%", thickness=2, color=ACCENT_COLOR,
        spaceAfter=4 * mm, spaceBefore=0
    ))

    # Contract number & date
    contract_date = datetime.utcnow().strftime("%B %d, %Y")
    booking_id = getattr(booking, 'id', 'N/A')
    created = getattr(booking, 'created_at', None)
    booking_date = created.strftime("%B %d, %Y") if created else contract_date

    header_data = [[
        Paragraph(f'<b>Contract #:</b> TC-{booking_id}', styles['Normal']),
        Paragraph(f'<b>Date:</b> {contract_date}', styles['Normal']),
    ]]
    header_table = Table(header_data, colWidths=[page_width / 2] * 2)
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))

    # ── Renter Information ──────────────────────────────────
    elements.append(Paragraph("RENTER INFORMATION", styles['SectionHeading']))

    renter_name = getattr(booking, 'contact_full_name', None) or "—"
    renter_email = getattr(booking, 'contact_email', None) or "—"
    renter_phone = getattr(booking, 'contact_phone', None) or "—"

    doc_type = getattr(booking, 'document_type', None) or "—"
    doc_number = getattr(booking, 'document_number', None) or "—"

    # User additional info
    license_number = "—"
    license_country = "—"
    date_of_birth = "—"
    if user:
        license_number = getattr(user, 'driver_license_number', None) or "—"
        license_country = getattr(user, 'driver_license_country', None) or "—"
        dob = getattr(user, 'date_of_birth', None)
        date_of_birth = dob.strftime("%B %d, %Y") if dob else "—"

    col_w = page_width / 3
    renter_rows = [
        [
            _field_pair("Full Name", renter_name, styles),
            _field_pair("Email", renter_email, styles),
            _field_pair("Phone", renter_phone, styles),
        ],
        [
            _field_pair("Document Type", doc_type.replace('_', ' ').title() if doc_type != "—" else "—", styles),
            _field_pair("Document Number", doc_number, styles),
            _field_pair("License Number", license_number, styles),
        ],
    ]

    for row in renter_rows:
        flat_row = []
        for pair in row:
            # Combine label + value into a single cell
            cell_content = [pair[0], pair[1]]
            flat_row.append(cell_content)
        data = [flat_row]
        t = Table(data, colWidths=[col_w] * 3)
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ]))
        elements.append(t)
    elements.append(Spacer(1, 2 * mm))

    # ── Vehicle Information ─────────────────────────────────
    elements.append(Paragraph("VEHICLE INFORMATION", styles['SectionHeading']))

    vehicle_name = "—"
    license_plate = "—"
    transmission = "—"

    if vehicle:
        brand = getattr(vehicle, 'brand_name', '') or ''
        model = getattr(vehicle, 'model_name', '') or ''
        vehicle_name = f"{brand} {model}".strip() or "—"
        license_plate = getattr(vehicle, 'license_plate', None) or "—"
        tr = getattr(vehicle, 'transmission', None)
        transmission = (tr.value if hasattr(tr, 'value') else str(tr or "—")).title()
    else:
        # Fallback: use vehicle_model + vehicle_group when no specific vehicle assigned
        if vehicle_model:
            brand = getattr(vehicle_model, 'brand', None)
            brand_name = getattr(brand, 'name', '') if brand else ''
            model_name = getattr(vehicle_model, 'name', '') or ''
            vehicle_name = f"{brand_name} {model_name}".strip() or "—"
        elif vehicle_group:
            vehicle_name = getattr(vehicle_group, 'name', None) or "—"

        if vehicle_group:
            tr = getattr(vehicle_group, 'transmission', None)
            if tr:
                transmission = tr.title()

    vehicle_rows = [
        [
            _field_pair("Vehicle", vehicle_name, styles),
            _field_pair("Transmission", transmission, styles),
            _field_pair("License Plate", license_plate, styles),
        ],
    ]

    for row in vehicle_rows:
        flat_row = []
        for pair in row:
            cell_content = [pair[0], pair[1]]
            flat_row.append(cell_content)
        data = [flat_row]
        t = Table(data, colWidths=[col_w] * 3)
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ]))
        elements.append(t)
    elements.append(Spacer(1, 2 * mm))

    # ── Rental Period & Locations ───────────────────────────
    elements.append(Paragraph("RENTAL PERIOD & LOCATIONS", styles['SectionHeading']))

    pickup_dt = getattr(booking, 'pickup_datetime', None)
    dropoff_dt = getattr(booking, 'dropoff_datetime', None)
    pickup_str = pickup_dt.strftime("%b %d, %Y  %H:%M") if pickup_dt else "—"
    dropoff_str = dropoff_dt.strftime("%b %d, %Y  %H:%M") if dropoff_dt else "—"

    rental_days = 0
    if pickup_dt and dropoff_dt:
        rental_days = max(1, (dropoff_dt - pickup_dt).days)

    pickup_loc_name = "—"
    dropoff_loc_name = "—"
    if pickup_location:
        pickup_loc_name = getattr(pickup_location, 'name', "—")
    if dropoff_location:
        dropoff_loc_name = getattr(dropoff_location, 'name', "—")

    period_rows = [
        [
            _field_pair("Pick-Up Date & Time", pickup_str, styles),
            _field_pair("Drop-Off Date & Time", dropoff_str, styles),
            _field_pair("Rental Duration", f"{rental_days} day{'s' if rental_days != 1 else ''}", styles),
        ],
        [
            _field_pair("Pick-Up Location", pickup_loc_name, styles),
            _field_pair("Drop-Off Location", dropoff_loc_name, styles),
            _field_pair("", "", styles),
        ],
    ]

    for row in period_rows:
        flat_row = []
        for pair in row:
            cell_content = [pair[0], pair[1]]
            flat_row.append(cell_content)
        data = [flat_row]
        t = Table(data, colWidths=[col_w] * 3)
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ]))
        elements.append(t)
    elements.append(Spacer(1, 2 * mm))

    # ── Pricing Breakdown ───────────────────────────────────
    elements.append(Paragraph("PRICING BREAKDOWN", styles['SectionHeading']))

    currency = getattr(booking, 'currency', 'EUR') or 'EUR'
    cur = currency.upper()
    price_per_day = float(getattr(booking, 'price_per_day', 0) or 0)
    base_rate = float(getattr(booking, 'base_rate', 0) or 0)
    one_way_fee = float(getattr(booking, 'one_way_fee', 0) or 0)
    delivery_fee = float(getattr(booking, 'delivery_fee', 0) or 0)
    deposit = float(getattr(booking, 'deposit', 0) or 0)
    discount_val = float(getattr(booking, 'discount', 0) or 0)
    taxes = float(getattr(booking, 'taxes', 0) or 0)
    fees = float(getattr(booking, 'fees', 0) or 0)
    total_amount = float(getattr(booking, 'total_amount', 0) or 0)

    # Build price rows
    price_data = [
        [
            Paragraph('<b>Description</b>', styles['Normal']),
            Paragraph('<b>Amount</b>', styles['Normal']),
        ],
    ]

    if price_per_day > 0:
        price_data.append([
            Paragraph(f"Daily Rate × {rental_days} day{'s' if rental_days != 1 else ''}", styles['Normal']),
            Paragraph(f"{cur} {price_per_day:.2f} / day", styles['Normal']),
        ])

    if base_rate > 0:
        price_data.append([
            Paragraph("Base Rental Charge", styles['Normal']),
            Paragraph(f"{cur} {base_rate:.2f}", styles['Normal']),
        ])

    # Extras
    if extras:
        for be in extras:
            extra_obj = getattr(be, 'extra', None)
            extra_name = getattr(extra_obj, 'name', 'Extra') if extra_obj else 'Extra'
            qty = getattr(be, 'quantity', 1)
            dp = float(getattr(be, 'daily_price', 0) or 0)
            extra_total = dp * qty * rental_days
            desc = f"{extra_name}"
            if qty > 1:
                desc += f" × {qty}"
            price_data.append([
                Paragraph(desc, styles['Normal']),
                Paragraph(f"{cur} {extra_total:.2f}", styles['Normal']),
            ])

    if one_way_fee > 0:
        price_data.append([
            Paragraph("One-Way Fee", styles['Normal']),
            Paragraph(f"{cur} {one_way_fee:.2f}", styles['Normal']),
        ])

    if delivery_fee > 0:
        price_data.append([
            Paragraph("Delivery Fee", styles['Normal']),
            Paragraph(f"{cur} {delivery_fee:.2f}", styles['Normal']),
        ])

    if taxes > 0:
        price_data.append([
            Paragraph("Taxes", styles['Normal']),
            Paragraph(f"{cur} {taxes:.2f}", styles['Normal']),
        ])

    if fees > 0:
        price_data.append([
            Paragraph("Additional Fees", styles['Normal']),
            Paragraph(f"{cur} {fees:.2f}", styles['Normal']),
        ])

    if discount_val > 0:
        price_data.append([
            Paragraph("Discount", styles['Normal']),
            Paragraph(f"- {cur} {discount_val:.2f}", styles['Normal']),
        ])

    # Deposit row
    if deposit > 0:
        price_data.append([
            Paragraph("Security Deposit", styles['Normal']),
            Paragraph(f"{cur} {deposit:.2f}", styles['Normal']),
        ])

    # Total row
    price_data.append([
        Paragraph('<b>TOTAL</b>', styles['Normal']),
        Paragraph(f'<b>{cur} {total_amount:.2f}</b>', styles['Normal']),
    ])

    price_table = Table(price_data, colWidths=[page_width * 0.65, page_width * 0.35])
    price_style = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        # Alternating rows
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LINEBELOW', (0, 0), (-1, -2), 0.25, BORDER_COLOR),
        # Total row highlight
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e8f4f8")),
        ('LINEABOVE', (0, -1), (-1, -1), 1, PRIMARY_COLOR),
    ]
    for i in range(1, len(price_data) - 1):
        if i % 2 == 0:
            price_style.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))

    price_table.setStyle(TableStyle(price_style))
    elements.append(price_table)
    elements.append(Spacer(1, 4 * mm))

    # ── Payment Status ──────────────────────────────────────
    payment_status = getattr(booking, 'payment_status', None)
    ps_str = "—"
    if payment_status:
        ps_str = (payment_status.value if hasattr(payment_status, 'value') else str(payment_status)).upper()

    booking_status = getattr(booking, 'status', None)
    bs_str = "—"
    if booking_status:
        bs_str = (booking_status.value if hasattr(booking_status, 'value') else str(booking_status)).replace('_', ' ').title()

    status_data = [[
        _field_pair("Booking Status", bs_str, styles),
        _field_pair("Payment Status", ps_str, styles),
        _field_pair("Deposit", f"{cur} {deposit:.2f}", styles),
    ]]

    flat_row = []
    for pair in status_data[0]:
        cell_content = [pair[0], pair[1]]
        flat_row.append(cell_content)
    st = Table([flat_row], colWidths=[col_w] * 3)
    st.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e8f4f8")),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 6 * mm))

    # ── Legal Terms & Conditions ────────────────────────────
    elements.append(HRFlowable(
        width="100%", thickness=1, color=PRIMARY_COLOR,
        spaceAfter=3 * mm, spaceBefore=2 * mm
    ))
    elements.append(Paragraph("TERMS AND CONDITIONS", styles['SectionHeading']))

    legal_sections = [
        ("1. Rental Agreement",
         "This Car Rental Agreement (\"Agreement\") is entered into between TbilisiCars LLC (\"Company\") "
         "and the Renter identified above. By signing this Agreement or accepting delivery of the vehicle, "
         "the Renter agrees to all terms and conditions stated herein."),

        ("2. Vehicle Condition & Inspection",
         "The Renter acknowledges receiving the vehicle in good condition and agrees to return it in the same "
         "condition, subject to normal wear and tear. Any pre-existing damage will be documented at the time of "
         "pick-up. The Renter must report any new damage immediately to the Company."),

        ("3. Insurance Coverage",
         "The rental includes comprehensive insurance coverage. The Renter is covered against third-party liability "
         "and vehicle damage subject to the terms of the insurance policy. The insurance does not cover: damage "
         "caused by driving under the influence of alcohol or drugs, damage to tires, interior damage caused by "
         "negligence, loss of personal belongings, or damage resulting from violation of traffic laws."),

        ("4. Driver Requirements",
         "The Renter must be at least 21 years of age and hold a valid driver's license recognized in Georgia. "
         "An International Driving Permit (IDP) is required for licenses not issued in Latin script. Only authorized "
         "drivers listed in this Agreement may operate the vehicle."),

        ("5. Usage Restrictions",
         "The vehicle shall not be used for: illegal purposes, racing or speed testing, towing, carrying hazardous "
         "materials, driving on unpaved roads unless the vehicle is classified as an SUV or 4×4, or transporting "
         "the vehicle outside of Georgia without prior written consent from the Company."),

        ("6. Fuel Policy",
         "Vehicles are delivered with a certain fuel level and must be returned with the same fuel level. "
         "If the vehicle is returned with much less fuel, refueling charges may apply."),

        ("7. Mileage",
         "Mileage is unlimited."),

        ("8. Security Deposit",
         "A security deposit may be held on the Renter's credit card or collected in cash at the time of pick-up. "
         "The deposit will be refunded within 7 business days if the deposit is frozen with a credit card; if paid in cash, "
         "the deposit is returned at drop-off. The vehicle must be returned in satisfactory condition, less any charges "
         "for damages, fines, or other liabilities."),

        ("9. Late Return",
         "If the vehicle is returned later than the agreed drop-off time, additional charges will apply. A grace "
         "period of 2 hours is allowed. If late or if there are changes about the drop-off time, the Renter must inform "
         "our colleagues in advance. If the Renter does not inform us or is late more than the 2-hour grace period, "
         "an additional day's rental may be charged. The Company reserves the right to report the vehicle as stolen "
         "if it is not returned within 12 hours of the agreed drop-off time."),

        ("10. Traffic Violations & Fines",
         "The Renter is responsible for all traffic violations, parking tickets, and fines incurred during the rental "
         "period. The Company may charge the Renter's credit card or deduct from the security deposit for any fines "
         "received after the rental period that relate to the Renter's use of the vehicle."),

        ("11. Breakdown & Roadside Assistance",
         "In case of vehicle breakdown or mechanical failure, the Renter must contact the Company immediately. "
         "The Company provides 24/7 roadside assistance. The Renter should not attempt to repair the vehicle or "
         "engage third-party services without prior authorization from the Company."),

        ("12. Cancellation Policy",
         "Cancellations are free of charge."),

        ("13. Limitation of Liability",
         "The Company's liability is limited to the replacement value of the vehicle. The Company is not liable for "
         "indirect, consequential, or special damages, including but not limited to loss of income, travel expenses, "
         "or accommodation costs arising from vehicle breakdown or unavailability."),

        ("14. Governing Law",
         "This Agreement is governed by the laws of Georgia. Any disputes arising from this Agreement shall be "
         "resolved through the courts of Tbilisi, Georgia."),

        ("15. Data Protection",
         "Personal data collected under this Agreement is processed in accordance with applicable data protection "
         "laws. The Company retains rental records for a period of 5 years for legal and regulatory purposes."),
    ]

    for heading, text in legal_sections:
        elements.append(Paragraph(heading, styles['LegalHeading']))
        elements.append(Paragraph(text, styles['LegalText']))

    elements.append(Spacer(1, 8 * mm))

    # ── Signature Section ───────────────────────────────────
    elements.append(HRFlowable(
        width="100%", thickness=1, color=PRIMARY_COLOR,
        spaceAfter=4 * mm, spaceBefore=2 * mm
    ))

    sig_data = [
        [
            Paragraph('<b>Renter Signature</b>', styles['Normal']),
            Paragraph('', styles['Normal']),
            Paragraph('<b>Company Representative</b>', styles['Normal']),
        ],
        [
            Paragraph('', styles['Normal']),
            Paragraph('', styles['Normal']),
            Paragraph('', styles['Normal']),
        ],
        [
            Paragraph('_' * 35, styles['Normal']),
            Paragraph('', styles['Normal']),
            Paragraph('_' * 35, styles['Normal']),
        ],
        [
            Paragraph(renter_name, styles['Normal']),
            Paragraph('', styles['Normal']),
            Paragraph('TbilisiCars LLC', styles['Normal']),
        ],
        [
            Paragraph(f'Date: {contract_date}', styles['FieldLabel']),
            Paragraph('', styles['Normal']),
            Paragraph(f'Date: {contract_date}', styles['FieldLabel']),
        ],
    ]

    sig_table = Table(sig_data, colWidths=[page_width * 0.4, page_width * 0.2, page_width * 0.4])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(sig_table)

    elements.append(Spacer(1, 8 * mm))

    # ── Footer ──────────────────────────────────────────────
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=BORDER_COLOR,
        spaceAfter=3 * mm
    ))
    elements.append(Paragraph(
        "TbilisiCars LLC  •  Tbilisi, Georgia  •  +995 591 00 26 30  •  info@tbilisicars.com",
        styles['FooterText']
    ))
    elements.append(Paragraph(
        f"Contract generated on {contract_date}  •  Contract Reference: TC-{booking_id}",
        styles['FooterText']
    ))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
