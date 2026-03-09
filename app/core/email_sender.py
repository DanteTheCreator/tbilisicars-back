"""
Service for sending booking confirmation emails to customers.
Uses Gmail API over HTTPS (bypasses SMTP port blocks on many VPS providers).

Supports two modes:
  1. Gmail API with OAuth2 service account (GOOGLE_SERVICE_ACCOUNT_FILE env var)
  2. Fallback to SMTP with app password (GMAIL_ADDRESS + GMAIL_APP_PASSWORD)
"""
from __future__ import annotations

import base64
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime


GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "/app/service-account.json")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _get_gmail_service():
    """Build a Gmail API service using a service account with domain-wide delegation."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        
        creds_path = GOOGLE_SERVICE_ACCOUNT_FILE
        if not os.path.exists(creds_path):
            print(f"[EMAIL] Service account file not found at {creds_path}")
            return None
        
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        # Delegate to the Gmail address
        delegated_credentials = credentials.with_subject(GMAIL_ADDRESS)
        
        service = build('gmail', 'v1', credentials=delegated_credentials, cache_discovery=False)
        return service
    except Exception as e:
        print(f"[EMAIL] Failed to build Gmail API service: {e}")
        return None


def _send_via_gmail_api(msg: MIMEMultipart, recipient: str) -> bool:
    """Send email via Gmail API over HTTPS."""
    service = _get_gmail_service()
    if not service:
        return False
    
    try:
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        body = {'raw': raw_message}
        service.users().messages().send(userId='me', body=body).execute()
        return True
    except Exception as e:
        print(f"[EMAIL] Gmail API send failed: {e}")
        return False


def _send_via_smtp(msg: MIMEMultipart, recipient: str) -> bool:
    """Send email via SMTP (original method, requires SMTP ports to be open)."""
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL] SMTP send failed: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL] SMTP send failed: {e}")
        return False


def _format_datetime(dt: datetime | str | None) -> str:
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return dt
    return dt.strftime("%B %d, %Y at %H:%M")


def _format_currency(amount: float | None, currency: str = "USD") -> str:
    if amount is None:
        return "N/A"
    amount = float(amount)
    symbol = "$" if currency == "USD" else currency + " "
    return f"{symbol}{amount:,.2f}"


def send_booking_confirmation(
    booking_id: int,
    customer_name: str,
    customer_email: str,
    pickup_datetime: datetime | str | None,
    dropoff_datetime: datetime | str | None,
    pickup_location: str,
    dropoff_location: str,
    total_amount: float | None,
    currency: str = "USD",
    rental_days: int | None = None,
    vehicle_group_name: str | None = None,
    pdf_attachment: bytes | None = None,
    one_way_fee: float = 0.0,
    delivery_fee: float = 0.0,
) -> bool:
    """
    Send a booking confirmation email to the customer.
    Optionally attaches a PDF contract if pdf_attachment bytes are provided.
    Returns True if sent successfully, False otherwise.
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[EMAIL] Gmail credentials not configured, skipping confirmation email")
        return False

    if not customer_email:
        print(f"[EMAIL] No email for booking #{booking_id}, skipping")
        return False

    msg = MIMEMultipart("mixed")
    msg["From"] = f"TbilisiCars <{GMAIL_ADDRESS}>"
    msg["To"] = customer_email
    msg["Subject"] = f"Booking Confirmation #{booking_id} — TbilisiCars"

    pickup_str = _format_datetime(pickup_datetime)
    dropoff_str = _format_datetime(dropoff_datetime)
    total_str = _format_currency(total_amount, currency)
    days_str = f"{rental_days} day{'s' if rental_days != 1 else ''}" if rental_days else ""
    vehicle_str = vehicle_group_name or "To be confirmed"
    one_way_fee_str = _format_currency(one_way_fee, currency) if one_way_fee else ""
    delivery_fee_str = _format_currency(delivery_fee, currency) if delivery_fee else ""

    # Plain text version
    text = f"""Hi {customer_name},

Thank you for choosing TbilisiCars! Your reservation is confirmed!
Please see the attached PDF for your confirmed contract.

BOOKING DETAILS
  Reservation #: {booking_id}
  Vehicle: {vehicle_str}
  Pick Up: {pickup_str}
  Pick Up Location: {pickup_location}
  Drop Off: {dropoff_str}
  Drop Off Location: {dropoff_location}
  Duration: {days_str}
{f'  One-Way Fee: {one_way_fee_str}' + chr(10) if one_way_fee else ''}{f'  Delivery Fee: {delivery_fee_str}' + chr(10) if delivery_fee else ''}  Estimated Total: {total_str}

NEED HELP?
  Phone: +995 591 00 26 30
  Email: {GMAIL_ADDRESS}

Thank you for trusting us with your Georgian adventure!

— The TbilisiCars Team
https://tbilisicars.live
"""

    # HTML version
    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
        <!-- Header -->
        <tr>
          <td style="background:#1a1a2e;padding:28px 32px;text-align:center;">
            <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:700;letter-spacing:0.5px;">TbilisiCars</h1>
            <p style="color:#a0a0b8;margin:6px 0 0;font-size:13px;">Your Georgian adventure starts here</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <p style="font-size:16px;color:#333;margin:0 0 8px;">Hi <strong>{customer_name}</strong>,</p>
            <p style="font-size:15px;color:#555;margin:0 0 24px;line-height:1.5;">Thank you for choosing TbilisiCars! Your reservation is confirmed! Please see the attached PDF for your confirmed contract.</p>

            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f9fb;border-radius:10px;padding:4px;">
              <tr>
                <td style="padding:20px 24px;">
                  <h2 style="margin:0 0 16px;font-size:17px;color:#1a1a2e;border-bottom:1px solid #e2e4e8;padding-bottom:10px;">Booking #{booking_id}</h2>
                  <table width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;color:#444;">
                    <tr>
                      <td style="padding:6px 0;color:#777;width:140px;">Vehicle</td>
                      <td style="padding:6px 0;font-weight:600;">{vehicle_str}</td>
                    </tr>
                    <tr>
                      <td style="padding:6px 0;color:#777;">Pick Up</td>
                      <td style="padding:6px 0;font-weight:600;">{pickup_str}</td>
                    </tr>
                    <tr>
                      <td style="padding:6px 0;color:#777;">Pick Up Location</td>
                      <td style="padding:6px 0;">{pickup_location}</td>
                    </tr>
                    <tr>
                      <td style="padding:6px 0;color:#777;">Drop Off</td>
                      <td style="padding:6px 0;font-weight:600;">{dropoff_str}</td>
                    </tr>
                    <tr>
                      <td style="padding:6px 0;color:#777;">Drop Off Location</td>
                      <td style="padding:6px 0;">{dropoff_location}</td>
                    </tr>
                    {"<tr><td style='padding:6px 0;color:#777;'>Duration</td><td style='padding:6px 0;'>" + days_str + "</td></tr>" if days_str else ""}
                    {"<tr><td style='padding:6px 0;color:#777;'>One-Way Fee</td><td style='padding:6px 0;'>" + one_way_fee_str + "</td></tr>" if one_way_fee else ""}
                    {"<tr><td style='padding:6px 0;color:#777;'>Delivery Fee</td><td style='padding:6px 0;'>" + delivery_fee_str + "</td></tr>" if delivery_fee else ""}
                    <tr>
                      <td style="padding:10px 0 6px;color:#777;border-top:1px solid #e2e4e8;">Estimated Total</td>
                      <td style="padding:10px 0 6px;font-weight:700;font-size:16px;color:#1a1a2e;border-top:1px solid #e2e4e8;">{total_str}</td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <div style="margin:24px 0;padding:16px 20px;background:#eef7ee;border-radius:8px;border-left:4px solid #4caf50;">
              <p style="margin:0;font-size:14px;color:#2e7d32;"><strong>Your contract is attached</strong></p>
              <p style="margin:6px 0 0;font-size:13px;color:#555;line-height:1.5;">Please review the attached PDF contract for full details of your reservation. If you have any questions, don't hesitate to reach out.</p>
            </div>

            <p style="font-size:13px;color:#999;margin:24px 0 0;line-height:1.5;">
              Questions? Reach us at <a href="tel:+995591002630" style="color:#1a73e8;">+995 591 00 26 30</a> or reply to this email.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8f9fb;padding:20px 32px;text-align:center;border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#999;">
              &copy; TbilisiCars &middot; <a href="https://tbilisicars.live" style="color:#1a73e8;text-decoration:none;">tbilisicars.live</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    # Wrap text and html in an alternative part
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(text, "plain"))
    msg_alt.attach(MIMEText(html, "html"))
    msg.attach(msg_alt)

    # Attach PDF contract if provided
    if pdf_attachment:
        pdf_part = MIMEApplication(pdf_attachment, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition", "attachment",
            filename=f"TbilisiCars_Contract_TC-{booking_id}.pdf"
        )
        msg.attach(pdf_part)

    try:
        # Try Gmail API first (works over HTTPS, bypasses SMTP port blocks)
        if os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            if _send_via_gmail_api(msg, customer_email):
                print(f"[EMAIL] Confirmation sent via Gmail API to {customer_email} for booking #{booking_id}")
                return True
            print(f"[EMAIL] Gmail API failed, falling back to SMTP...")
        
        # Fallback to SMTP
        if GMAIL_APP_PASSWORD:
            if _send_via_smtp(msg, customer_email):
                print(f"[EMAIL] Confirmation sent via SMTP to {customer_email} for booking #{booking_id}")
                return True
        
        print(f"[EMAIL] All send methods failed for booking #{booking_id}")
        return False
    except Exception as e:
        print(f"[EMAIL] Failed to send confirmation for booking #{booking_id}: {e}")
        return False
