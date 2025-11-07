"""Background email monitoring service"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.config import get_settings
from app.email_parsers.gmail_client import GmailClient
from app.email_parsers.processor import EmailBookingProcessor

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailMonitorService:
    """Background service to monitor Gmail for booking emails"""
    
    def __init__(self, check_interval: Optional[int] = None):
        """
        Initialize email monitor
        
        Args:
            check_interval: Seconds between email checks (default: from config)
        """
        self.check_interval = check_interval or settings.EMAIL_CHECK_INTERVAL
        self.gmail_client: Optional[GmailClient] = None
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the email monitoring service"""
        if self.is_running:
            logger.warning("Email monitor already running")
            return
        
        logger.info("Starting email monitoring service")
        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Stop the email monitoring service"""
        logger.info("Stopping email monitoring service")
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        # Initialize Gmail client
        try:
            self.gmail_client = GmailClient()
            self.gmail_client.authenticate()
            logger.info("Gmail client authenticated successfully")
        except Exception as e:
            logger.error(f"Failed to authenticate Gmail client: {e}")
            logger.warning("Email monitoring disabled - Gmail credentials not configured")
            self.is_running = False
            return
        
        while self.is_running:
            try:
                await self._check_emails()
            except Exception as e:
                logger.error(f"Error checking emails: {e}")
            
            # Wait before next check
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
    
    async def _check_emails(self):
        """Check for new emails and process them"""
        db: Session = SessionLocal()
        
        try:
            processor = EmailBookingProcessor(db, self.gmail_client)
            
            # Process unread emails
            results = processor.process_unread_emails(max_emails=20)
            
            if results['processed'] > 0:
                logger.info(
                    f"Email check complete: {results['processed']} processed, "
                    f"{results['created']} bookings created, "
                    f"{results['failed']} failed, "
                    f"{results['skipped']} skipped"
                )
                
                if results['errors']:
                    for error in results['errors']:
                        logger.error(f"Email processing error: {error}")
            
        except Exception as e:
            logger.error(f"Failed to process emails: {e}")
        finally:
            db.close()


# Global service instance
email_monitor_service = EmailMonitorService()
