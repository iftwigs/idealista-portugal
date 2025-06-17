# Tests Directory

This directory contains all test files for the Idealista Notifier Bot project.

## Test Categories

### Core Functionality Tests
- `test_models.py` - Tests for SearchConfig and data models
- `test_scraper.py` - Basic scraper functionality tests  
- `test_scraper_enhanced.py` - Enhanced scraper tests with mocking
- `test_bot.py` - Telegram bot functionality tests
- `test_bot_flow.py` - Bot conversation flow tests

### Feature-Specific Tests
- `test_pagination_behavior.py` - Comprehensive pagination tests
- `test_pagination_debug.py` - Debug tests for pagination
- `test_pagination_url_construction.py` - URL construction tests
- `test_furniture_filtering.py` - Furniture filter tests
- `test_url_generation.py` - URL parameter generation tests
- `test_adaptive_rate_limiting.py` - Rate limiting tests
- `test_user_stats.py` - User statistics tests

### Integration Tests
- `test_integration_complete.py` - End-to-end integration tests
- `test_new_bot_features.py` - Tests for new bot features
- `test_configuration_validation.py` - Configuration validation tests
- `test_monitoring_debugging.py` - Monitoring and debugging tests

## Running Tests

### Using pytest (recommended)
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_pagination_behavior.py -v

# Run with coverage
python -m pytest tests/ -v --cov=src

# Run specific test method
python -m pytest tests/test_pagination_behavior.py::TestPaginationBehavior::test_pagination_scrapes_all_pages_with_force_all_pages -v
```

### Running individual test files
```bash
# Run a single test file directly
python tests/test_furniture_filtering.py

# Run pagination debug tests
python tests/test_pagination_debug.py

# Run URL construction tests
python tests/test_pagination_url_construction.py
```

## Test Structure

All tests follow these conventions:
- Test files start with `test_`
- Test classes start with `Test`
- Test methods start with `test_`
- Fixtures are used for common setup
- Mocking is used to isolate functionality

## Important Notes

1. **Import Path Setup**: All test files automatically add the `src/` directory to the Python path
2. **Async Tests**: Many tests use `@pytest.mark.asyncio` for async functionality
3. **Mocking**: Tests extensively use `unittest.mock` to avoid making real HTTP requests
4. **Fixtures**: Common test objects are created using pytest fixtures

## Test Dependencies

Tests require these additional packages (install with `pip install -r requirements.txt`):
- `pytest`
- `pytest-asyncio` 
- `pytest-cov` (for coverage)
- `unittest.mock` (built-in)

## Coverage

To generate test coverage reports:
```bash
# Generate coverage report
python -m pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Debugging Tests

To debug failing tests:
```bash
# Run with verbose output and stop on first failure
python -m pytest tests/ -v -x

# Run with pdb debugger
python -m pytest tests/test_pagination_behavior.py --pdb

# Run specific failing test with debug output
python tests/test_pagination_debug.py
```