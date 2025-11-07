"""Simple IMAP email client using app password"""
from __future__ import annotations

import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any
import os


class GmailClient:
    """Simple Gmail IMAP client using app password"""
    
    def __init__(self, email_address: str = None, app_password: str = None):
        """
        Initialize Gmail IMAP client
        
        Args:
            email_address: Gmail address
            app_password: Gmail app password (16 chars without spaces)
        """
        self.email_address = email_address or os.getenv('GMAIL_ADDRESS')
        self.app_password = app_password or os.getenv('GMAIL_APP_PASSWORD')
        self.imap = None
        self.service = None  # For compatibility with old code
    
    def authenticate(self) -> None:
        """Authenticate with Gmail IMAP"""
        if not self.email_address or not self.app_password:
            raise ValueError("Gmail address and app password required")
        
        # Remove spaces from app password
        password = self.app_password.replace(' ', '')
        
        # Connect to Gmail IMAP
        self.imap = imaplib.IMAP4_SSL("imap.gmail.com")
        self.imap.login(self.email_address, password)
        self.service = True  # For compatibility
    
    def fetch_unread_emails(self, label: str = "INBOX", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from Gmail
        
        Args:
            label: Mailbox to search (default: INBOX)
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries
        """
        if not self.imap:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        self.imap.select(label)
        
        # Search for unread emails
        status, messages = self.imap.search(None, 'UNSEEN')
        
        if status != 'OK':
            return []
        
        email_ids = messages[0].split()
        emails = []
        
        # Fetch most recent emails first
        for email_id in reversed(email_ids[:max_results]):
            try:
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)
            except Exception as e:
                print(f"Error fetching email {email_id}: {e}")
        
        return emails
    
    def _fetch_email(self, email_id: bytes) -> Dict[str, Any]:
        """Fetch and parse a single email"""
        status, msg_data = self.imap.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            return None
        
        # Parse email
        msg = email.message_from_bytes(msg_data[0][1])
        
        # Get subject
        subject = self._decode_header(msg.get('Subject', ''))
        
        # Get from
        from_header = self._decode_header(msg.get('From', ''))
        
        # Get date
        date = msg.get('Date', '')
        
        # Get body
        body = self._get_email_body(msg)
        
        return {
            'id': email_id.decode(),
            'subject': subject,
            'from': from_header,
            'body': body,
            'date': date
        }
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                result.append(part)
        
        return ''.join(result)
    
    def _get_email_body(self, msg) -> str:
        """Extract email body"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())
        
        return body
    
    def mark_as_read(self, message_id: str) -> None:
        """Mark an email as read"""
        try:
            self.imap.store(message_id.encode(), '+FLAGS', '\\Seen')
        except Exception as e:
            print(f"Error marking email as read: {e}")
    
    def mark_with_label(self, message_id: str, label_name: str) -> None:
        """Add a label to an email (Gmail-specific)"""
        # IMAP doesn't support Gmail labels directly
        # You would need to use Gmail API for this
        pass
