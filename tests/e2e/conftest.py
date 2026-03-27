"""
HigherMatch™ E2E Tests - Pytest Configuration
============================================

Pytest fixtures and configuration for Playwright E2E tests.

版本: 1.0.0
"""

import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright


# ==================== Test Configuration ====================

# Base URLs
EMPLOYER_PORTAL_URL = os.getenv("EMPLOYER_PORTAL_URL", "http://localhost:5173")
CANDIDATE_PORTAL_URL = os.getenv("CANDIDATE_PORTAL_URL", "http://localhost:5174")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Test timeouts
DEFAULT_TIMEOUT = 30000  # 30 seconds
SHORTLIST_POLL_TIMEOUT = 60000  # 60 seconds for polling
SHORTLIST_POLL_INTERVAL = 5000  # 5 seconds between polls


# ==================== Playwright Setup ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def playwright() -> AsyncGenerator[Playwright, None]:
    """Initialize Playwright instance."""
    async with async_playwright() as p:
        yield p


@pytest_asyncio.fixture(scope="session")
async def browser(playwright: Playwright) -> AsyncGenerator[Browser, None]:
    """Launch browser instance."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ],
    )
    yield browser
    await browser.close()


@pytest_asyncio.fixture(scope="session")
async def browser_context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create browser context with default settings."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    yield context
    await context.close()


# ==================== Page Fixtures ====================

@pytest_asyncio.fixture
async def employer_page(browser_context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for employer portal tests."""
    page = await browser_context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    yield page
    await page.close()


@pytest_asyncio.fixture
async def candidate_page(browser_context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for candidate portal tests."""
    page = await browser_context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    yield page
    await page.close()


# ==================== Authentication Fixtures ====================

@pytest_asyncio.fixture
async def employer_auth(employer_page: Page) -> dict:
    """
    Employer authentication fixture.

    Returns auth info including token for API calls.
    """
    return EmployerAuth(employer_page)


@pytest_asyncio.fixture
async def candidate_auth(candidate_page: Page) -> dict:
    """
    Candidate authentication fixture.

    Returns auth info including token for API calls.
    """
    return CandidateAuth(candidate_page)


class EmployerAuth:
    """Helper class for employer authentication."""

    def __init__(self, page: Page):
        self.page = page
        self.token: str = None
        self.user_id: str = None

    async def login(self, email: str, password: str) -> bool:
        """
        Login as employer.

        Args:
            email: Employer email
            password: Password

        Returns:
            True if login successful
        """
        await self.page.goto(f"{EMPLOYER_PORTAL_URL}/employer/login")
        await self.page.wait_for_load_state("networkidle")

        # Fill login form
        await self.page.fill('input[type="email"]', email)
        await self.page.fill('input[type="password"]', password)
        await self.page.click('button[type="submit"]')

        # Wait for redirect to dashboard
        try:
            await self.page.wait_for_url(f"{EMPLOYER_PORTAL_URL}/employer/dashboard", timeout=10000)
            self.token = await self.page.evaluate("() => localStorage.getItem('access_token')")
            self.user_id = await self.page.evaluate("() => JSON.parse(localStorage.getItem('user_info') || '{}').id")
            return True
        except Exception:
            return False

    async def logout(self):
        """Logout employer."""
        await self.page.evaluate("() => { localStorage.removeItem('access_token'); localStorage.removeItem('user_info'); }")

    def get_headers(self) -> dict:
        """Get auth headers for API calls."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }


class CandidateAuth:
    """Helper class for candidate authentication."""

    def __init__(self, page: Page):
        self.page = page
        self.token: str = None
        self.user_id: str = None

    async def login(self, phone: str, code: str = "123456") -> bool:
        """
        Login as candidate with phone verification.

        Args:
            phone: Candidate phone number
            code: Verification code (mock)

        Returns:
            True if login successful
        """
        await self.page.goto(f"{CANDIDATE_PORTAL_URL}/login")
        await self.page.wait_for_load_state("networkidle")

        # Fill phone
        await self.page.fill('input[type="tel"]', phone)

        # Click send code button
        await self.page.click('button:has-text("获取验证码")')

        # Wait for code input
        await self.page.wait_for_selector('input[placeholder*="验证码"]', timeout=5000)

        # Fill mock code
        await self.page.fill('input[placeholder*="验证码"]', code)

        # Submit
        await self.page.click('button[type="submit"]')

        # Wait for redirect
        try:
            await self.page.wait_for_url(f"{CANDIDATE_PORTAL_URL}/recommendations", timeout=10000)
            self.token = await self.page.evaluate("() => localStorage.getItem('access_token')")
            self.user_id = await self.page.evaluate("() => JSON.parse(localStorage.getItem('user_info') || '{}').id")
            return True
        except Exception:
            return False

    async def logout(self):
        """Logout candidate."""
        await self.page.evaluate("() => { localStorage.removeItem('access_token'); localStorage.removeItem('user_info'); }")

    def get_headers(self) -> dict:
        """Get auth headers for API calls."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }


# ==================== API Helpers ====================

@pytest_asyncio.fixture
async def api_client():
    """API client for direct backend calls."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        yield APIClient(session)


class APIClient:
    """Helper for making API calls during tests."""

    def __init__(self, session):
        self.session = session
        self.base_url = API_BASE_URL
        self.token: str = None

    def set_token(self, token: str):
        """Set authentication token."""
        self.token = token

    async def post(self, path: str, json: dict = None, headers: dict = None) -> dict:
        """Make POST request."""
        auth_headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if headers:
            auth_headers.update(headers)

        async with self.session.post(
            f"{self.base_url}{path}",
            json=json,
            headers=auth_headers,
        ) as resp:
            return await resp.json()

    async def get(self, path: str, params: dict = None, headers: dict = None) -> dict:
        """Make GET request."""
        auth_headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if headers:
            auth_headers.update(headers)

        async with self.session.get(
            f"{self.base_url}{path}",
            params=params,
            headers=auth_headers,
        ) as resp:
            return await resp.json()


# ==================== Test Data Fixtures ====================

@pytest.fixture
def test_employer_data() -> dict:
    """Generate test employer data."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return {
        "email": f"test.employer.{timestamp}@highermatch.com",
        "password": "Test123456!",
        "company_name": f"测试公司_{timestamp}",
        "contact_person": "测试用户",
        "phone": f"1380000{timestamp[-4:]}",
    }


@pytest.fixture
def test_candidate_data() -> dict:
    """Generate test candidate data."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return {
        "phone": f"1390000{timestamp[-4:]}",
        "name": f"测试候选人_{timestamp}",
        "expected_salary_min": 20000,
        "expected_salary_max": 30000,
        "work_experience_years": 3,
    }


@pytest.fixture
def test_job_data() -> dict:
    """Generate test job posting data."""
    return {
        "title": "Python工程师",
        "city": "北京",
        "salary_min": 20000,
        "salary_max": 30000,
        "experience_years": 3,
        "description": "3年Python工程师，北京，20-30k",
    }


@pytest.fixture
def dummy_resume_path() -> str:
    """Get path to dummy resume file."""
    return os.path.join(os.path.dirname(__file__), "dummy_resume.pdf")


# ==================== Helper Functions ====================

async def wait_for_element(page: Page, selector: str, timeout: int = DEFAULT_TIMEOUT):
    """Wait for element to be visible."""
    await page.wait_for_selector(selector, state="visible", timeout=timeout)


async def wait_for_navigation(page: Page, timeout: int = DEFAULT_TIMEOUT):
    """Wait for page navigation to complete."""
    await page.wait_for_load_state("networkidle", timeout=timeout)


def extract_invoice_amount(page: Page) -> float:
    """Extract invoice amount from page text."""
    import re
    text = page.content()
    match = re.search(r"¥?\s*([\d,]+\.?\d*)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return 0.0
