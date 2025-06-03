import pytest

def pytest_configure(config):
    """Configure pytest-asyncio."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark a test as an async test"
    ) 