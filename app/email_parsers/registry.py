"""Registry for email parsers"""
from __future__ import annotations

from typing import List, Optional

from .base import BaseEmailParser, ParsedBookingData


class ParserRegistry:
    """Registry to manage and route emails to appropriate parsers"""
    
    def __init__(self):
        self._parsers: List[BaseEmailParser] = []
    
    def register(self, parser: BaseEmailParser) -> None:
        """Register a new parser"""
        self._parsers.append(parser)
    
    def find_parser(self, email_subject: str, email_body: str, email_from: str) -> Optional[BaseEmailParser]:
        """
        Find the appropriate parser for an email
        
        Args:
            email_subject: Email subject line
            email_body: Email body
            email_from: Sender email address
            
        Returns:
            Parser that can handle the email, or None
        """
        for parser in self._parsers:
            if parser.can_parse(email_subject, email_body, email_from):
                return parser
        return None
    
    def parse_email(self, email_subject: str, email_body: str, email_from: str) -> Optional[ParsedBookingData]:
        """
        Parse email using appropriate parser
        
        Args:
            email_subject: Email subject line
            email_body: Email body
            email_from: Sender email address
            
        Returns:
            ParsedBookingData if successful, None if no parser found
            
        Raises:
            ValueError: If parser found but parsing fails
        """
        parser = self.find_parser(email_subject, email_body, email_from)
        if parser is None:
            return None
        
        return parser.parse(email_subject, email_body, email_from)
    
    def list_brokers(self) -> List[str]:
        """Get list of registered broker names"""
        return [p.broker_name for p in self._parsers]


# Global registry instance
registry = ParserRegistry()
