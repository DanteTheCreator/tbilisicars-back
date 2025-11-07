"""
Email parsers for different brokers.
Each broker has its own parser implementation.
"""
from .example_broker import ExampleBrokerParser
# Import other parsers as they are created
# from .broker_a import BrokerAParser
# from .broker_b import BrokerBParser

__all__ = ["ExampleBrokerParser"]
