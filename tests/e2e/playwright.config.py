"""
HigherMatch™ E2E Tests - Playwright Configuration
==============================================

Playwright configuration for E2E tests.

Usage:
    playwright install chromium
    pytest tests/e2e/ --config=playwright.config.py
"""

from playwright.sync_api import sync_playwright


def pytest_configure(config):
    """Configure Playwright for pytest."""
    pass


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--browser",
        action="store",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser to run tests on",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode",
    )
    parser.addoption(
        "--slow-mo",
        action="store",
        default=0,
        type=int,
        help="Slow down operations by ms",
    )


@pytest.fixture(scope="session")
def browser_type(browser_type):
    """Get browser type from command line."""
    return browser_type


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Get browser context args."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }
