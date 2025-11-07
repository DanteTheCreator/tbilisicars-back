"""Initialize and register all email parsers"""
from .registry import registry
from .vipcars import VIPCarsParser
from .discover_cars import DiscoverCarsParser


def register_all_parsers():
    """Register all available parsers"""
    registry.register(VIPCarsParser())
    registry.register(DiscoverCarsParser())


# Auto-register on import
register_all_parsers()
