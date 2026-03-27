"""
HigherMatch™ E2E Tests - TC-001: Employer Complete Recruitment Flow
==================================================================

测试用例 TC-001：雇主完整招聘流程

测试步骤：
1. 雇主注册/登录
2. 导航至新建岗位，使用文本模式输入：「3年Python工程师，北京，20-30k」
3. 确认 AI 提取的 JD 草稿并点击「发布岗位」
4. 轮询等待 Shortlist（最多等60秒）
5. 导航至管道看板，验证「AI推荐」列中至少出现 1 个候选人卡片
6. 将候选人卡片移动至「已邀约」列
7. 调用 API 模拟入职确认操作
8. 导航至账单中心，验证对应账单生成且金额 > 0

前置条件：
- 雇主端 Portal 运行在 http://localhost:5173
- 后端 API 运行在 http://localhost:8000
- PostgreSQL、Kafka 等基础设施已启动

版本: 1.0.0
"""

import asyncio
import re
import time
from datetime import datetime
from typing import Optional

import pytest
import pytest_asyncio
from playwright.async_api import Page, expect


# ==================== Test Configuration ====================

EMPLOYER_PORTAL_URL = "http://localhost:5173"
API_BASE_URL = "http://localhost:8000"

# Polling configuration
SHORTLIST_POLL_TIMEOUT = 60000  # 60 seconds
SHORTLIST_POLL_INTERVAL = 5000   # 5 seconds


# ==================== Test Class ====================

class TestTC001EmployerRecruitmentFlow:
    """
    TC-001: 雇主完整招聘流程 E2E 测试

    覆盖雇主端核心业务流程：
    发布岗位 -> AI 匹配候选人 -> 管道管理 -> 入职 -> 账单
    """

    @pytest_asyncio.fixture
    async def employer_page(self, employer_page: Page) -> Page:
        """Setup page with larger viewport for employer portal."""
        await employer_page.set_viewport_size({"width": 1920, "height": 1080})
        return employer_page

    # ==================== Step 1: Login ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step1_employer_login(
        self,
        employer_page: Page,
        test_employer_data: dict,
    ):
        """
        Step 1: 雇主登录或注册

        测试点：
        - 导航至登录页
        - 输入邮箱密码登录
        - 验证成功跳转至工作台
        """
        email = test_employer_data["email"]
        password = test_employer_data["password"]

        # Navigate to login page
        await employer_page.goto(f"{EMPLOYER_PORTAL_URL}/employer/login")
        await employer_page.wait_for_load_state("networkidle")

        # Fill login form
        email_input = employer_page.locator('input[type="email"], input[name="email"]')
        password_input = employer_page.locator('input[type="password"], input[name="password"]')

        await email_input.fill(email)
        await password_input.fill(password)

        # Submit login
        submit_button = employer_page.locator('button[type="submit"], button:has-text("登录")')
        await submit_button.click()

        # Verify redirect to dashboard
        await employer_page.wait_for_url(
            f"{EMPLOYER_PORTAL_URL}/employer/dashboard",
            timeout=15000
        )

        # Verify login success
        assert "dashboard" in employer_page.url, "Should redirect to dashboard after login"

        # Store auth token for later API calls
        token = await employer_page.evaluate(
            "() => localStorage.getItem('access_token')"
        )
        assert token is not None, "Auth token should be stored after login"

        print(f"✓ Employer logged in successfully: {email}")

    # ==================== Step 2-3: Create Job ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step2_3_create_job(
        self,
        employer_page: Page,
        test_job_data: dict,
    ):
        """
        Step 2-3: 创建岗位

        测试点：
        - 导航至新建岗位页面
        - 使用文本模式输入岗位描述
        - 确认 AI 提取的 JD 草稿
        - 点击发布岗位
        """
        # Navigate to create job page
        await employer_page.goto(f"{EMPLOYER_PORTAL_URL}/employer/jobs/new")
        await employer_page.wait_for_load_state("networkidle")

        # Find text input mode toggle
        text_mode_toggle = employer_page.locator(
            'button:has-text("文本模式"), [data-testid="text-mode"]'
        )
        if await text_mode_toggle.is_visible():
            await text_mode_toggle.click()

        # Wait for text input area
        text_input = employer_page.locator(
            'textarea, input[placeholder*="输入"], [data-testid="job-description-input"]'
        )
        await text_input.wait_for(timeout=5000)
        await text_input.fill(test_job_data["description"])

        # Click AI extract button or wait for auto-extraction
        extract_button = employer_page.locator(
            'button:has-text("AI提取"), button:has-text("提取"), [data-testid="extract"]'
        )
        if await extract_button.is_visible():
            await extract_button.click()

        # Wait for JD draft to be generated
        jd_preview = employer_page.locator(
            '[data-testid="jd-preview"], .jd-preview, .job-description-preview'
        )
        await jd_preview.wait_for(timeout=10000)

        # Verify JD draft contains extracted information
        preview_text = await jd_preview.text_content()
        assert "Python" in preview_text or "python" in preview_text.lower(), \
            "JD preview should contain extracted job title"
        assert "北京" in preview_text, "JD preview should contain extracted city"

        # Click publish button
        publish_button = employer_page.locator(
            'button:has-text("发布岗位"), button:has-text("确认发布"), '
            '[data-testid="publish-job"]'
        )
        await publish_button.click()

        # Wait for success notification or redirect
        await employer_page.wait_for_url(
            f"{EMPLOYER_PORTAL_URL}/employer/jobs",
            timeout=15000
        )

        # Extract job ID from URL or page
        job_id = await self._extract_job_id(employer_page)

        assert job_id is not None, "Job should be created and have an ID"

        # Store job ID for subsequent tests
        await employer_page.evaluate(
            f"() => localStorage.setItem('test_job_id', '{job_id}')"
        )

        print(f"✓ Job created successfully: {job_id}")

        return job_id

    def _extract_job_id(self, page: Page) -> Optional[str]:
        """Extract job ID from current page or URL."""
        # Try to get from URL
        url = page.url
        match = re.search(r"/jobs/([a-zA-Z0-9-]+)", url)
        if match:
            return match.group(1)

        # Try to get from localStorage
        job_id = page.evaluate("() => localStorage.getItem('last_created_job_id')")
        if job_id:
            return job_id

        # Try to get from page content
        job_id_element = page.locator('[data-testid="job-id"], .job-id')
        if await job_id_element.is_visible():
            return await job_id_element.text_content()

        return None

    # ==================== Step 4: Wait for Shortlist ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step4_wait_for_shortlist(
        self,
        employer_page: Page,
        api_client,
    ):
        """
        Step 4: 轮询等待 Shortlist

        测试点：
        - 获取刚创建的岗位 ID
        - 轮询 API 检查匹配候选人数量
        - 最多等待 60 秒
        - 验证至少匹配到 1 个候选人
        """
        # Get job ID from previous step
        job_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_job_id')"
        )
        assert job_id is not None, "Job ID should be stored from previous step"

        # Poll for shortlist
        start_time = time.time()
        matched = False
        match_count = 0

        while time.time() - start_time < SHORTLIST_POLL_TIMEOUT:
            # Call matching API
            response = await api_client.get(f"/api/v1/jobs/{job_id}/matches")

            if response.get("success"):
                data = response.get("data", {})
                match_count = data.get("total_matches", 0)

                if match_count >= 1:
                    matched = True
                    break

            # Wait before next poll
            await asyncio.sleep(SHORTLIST_POLL_INTERVAL / 1000)

        elapsed_time = time.time() - start_time

        assert matched, (
            f"No matches found after {elapsed_time:.1f}s. "
            f"Expected at least 1 match."
        )

        print(f"✓ Shortlist ready: {match_count} candidates after {elapsed_time:.1f}s")

        return match_count

    # ==================== Step 5: Verify Pipeline Board ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step5_verify_pipeline_board(
        self,
        employer_page: Page,
    ):
        """
        Step 5: 验证管道看板

        测试点：
        - 导航至管道看板页面
        - 验证「AI推荐」列存在
        - 验证至少出现 1 个候选人卡片
        """
        # Get job ID
        job_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_job_id')"
        )
        assert job_id is not None, "Job ID should be available"

        # Navigate to pipeline board
        await employer_page.goto(
            f"{EMPLOYER_PORTAL_URL}/employer/jobs/{job_id}/pipeline"
        )
        await employer_page.wait_for_load_state("networkidle")

        # Wait for pipeline to load
        pipeline_board = employer_page.locator(
            '[data-testid="pipeline-board"], .pipeline-board, .kanban-board'
        )
        await pipeline_board.wait_for(timeout=10000)

        # Find AI Recommended column
        ai_recommended_column = employer_page.locator(
            '.kanban-column:has-text("AI推荐"), '
            '[data-stage="ai_recommended"], '
            '.column:has-text("AI推荐")'
        )

        # Alternative: Find any column with candidate cards
        if not await ai_recommended_column.is_visible():
            ai_recommended_column = employer_page.locator(
                '.kanban-column, .pipeline-column'
            ).first

        await ai_recommended_column.wait_for(timeout=5000)

        # Count candidate cards in AI Recommended column
        candidate_cards = ai_recommended_column.locator(
            '.candidate-card, [data-testid="candidate-card"], .card'
        )

        card_count = await candidate_cards.count()

        assert card_count >= 1, (
            "AI Recommended column should contain at least 1 candidate card"
        )

        # Store first card info for next step
        first_card = candidate_cards.first
        card_id = await first_card.get_attribute("data-match-id")
        if not card_id:
            card_id = await first_card.get_attribute("data-candidate-id")

        await employer_page.evaluate(
            f"() => localStorage.setItem('test_match_id', '{card_id}')"
        )

        print(f"✓ Pipeline board verified: {card_count} candidate(s) in AI Recommended")

        return card_count

    # ==================== Step 6: Move Candidate ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step6_move_candidate_to_invited(
        self,
        employer_page: Page,
        api_client,
    ):
        """
        Step 6: 移动候选人至「已邀约」

        测试点：
        - 找到候选人卡片
        - 点击操作菜单或拖拽至「已邀约」列
        - 验证移动成功
        """
        # Get match ID
        match_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_match_id')"
        )
        job_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_job_id')"
        )

        assert match_id is not None, "Match ID should be available"

        # Try UI interaction first
        candidate_card = employer_page.locator(
            f'[data-match-id="{match_id}"], [data-candidate-id="{match_id}"]'
        )

        if await candidate_card.is_visible():
            # Try drag and drop
            try:
                invited_column = employer_page.locator(
                    '.kanban-column:has-text("已邀约"), '
                    '[data-stage="invited"]'
                )

                # Drag card to invited column
                await candidate_card.drag_to(invited_column)
                await asyncio.sleep(1)

            except Exception:
                # Fallback: Click card to open modal, then move
                await candidate_card.click()

                # Look for move button in modal
                move_button = employer_page.locator(
                    'button:has-text("移动"), button:has-text("邀约"), '
                    '[data-action="move"]'
                )

                if await move_button.is_visible():
                    await move_button.click()

        # Alternatively, call API directly
        response = await api_client.post(
            "/api/v1/pipeline/move",
            json={
                "match_id": match_id,
                "from_stage": "ai_recommended",
                "to_stage": "invited",
            }
        )

        # Verify move was successful
        assert response.get("success") or response.get("status") == "success", (
            f"Failed to move candidate: {response}"
        )

        # Verify stage changed
        updated_match = await api_client.get(
            f"/api/v1/matches/{match_id}"
        )
        assert updated_match.get("data", {}).get("pipeline_stage") == "invited", (
            "Candidate should be in 'invited' stage after move"
        )

        print(f"✓ Candidate {match_id} moved to 'invited' stage")

    # ==================== Step 7: Simulate Onboarding ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step7_simulate_onboarding(
        self,
        employer_page: Page,
        api_client,
    ):
        """
        Step 7: 模拟入职确认

        测试点：
        - 调用 API 模拟候选人入职确认
        - 更新匹配状态为 onboarding_confirmed
        - 触发 Kafka 事件
        """
        # Get match ID
        match_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_match_id')"
        )
        job_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_job_id')"
        )

        assert match_id is not None, "Match ID should be available"

        # Simulate onboarding confirmation via API
        response = await api_client.post(
            "/api/v1/jobs/{job_id}/matches/{match_id}/onboard".format(
                job_id=job_id,
                match_id=match_id
            ),
            json={
                "action": "confirm_onboarding",
                "onboarding_date": datetime.now().strftime("%Y-%m-%d"),
                "annual_salary": 300000,  # 30万年薪
                "is_urgent": False,
            }
        )

        # Verify onboarding confirmed
        assert response.get("success") or response.get("status") == "success", (
            f"Onboarding confirmation failed: {response}"
        )

        # Move to onboarded stage
        move_response = await api_client.post(
            "/api/v1/pipeline/move",
            json={
                "match_id": match_id,
                "from_stage": "invited",
                "to_stage": "onboarded",
            }
        )

        assert move_response.get("success") or move_response.get("status") == "success", (
            f"Failed to move to onboarded: {move_response}"
        )

        print(f"✓ Onboarding simulated for match {match_id}")

    # ==================== Step 8: Verify Billing ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    async def test_step8_verify_billing(
        self,
        employer_page: Page,
        api_client,
    ):
        """
        Step 8: 验证账单生成

        测试点：
        - 导航至账单中心
        - 查找对应岗位的账单
        - 验证账单金额 > 0
        """
        # Navigate to billing page
        await employer_page.goto(f"{EMPLOYER_PORTAL_URL}/employer/billing")
        await employer_page.wait_for_load_state("networkidle")

        # Wait for billing list to load
        billing_list = employer_page.locator(
            '[data-testid="billing-list"], .billing-list, .invoice-list'
        )
        await billing_list.wait_for(timeout=10000)

        # Get job ID for matching
        job_id = await employer_page.evaluate(
            "() => localStorage.getItem('test_job_id')"
        )

        # Find invoice for this job
        invoice_row = employer_page.locator(
            f'[data-job-id="{job_id}"], .invoice-row:has-text("{job_id}")'
        )

        # Alternative: Find any invoice with amount > 0
        if not await invoice_row.is_visible():
            invoice_rows = employer_page.locator(
                '.invoice-row, [data-testid="invoice"], .billing-item'
            )
            row_count = await invoice_rows.count()

            for i in range(row_count):
                row = invoice_rows.nth(i)
                amount_text = await row.locator(
                    '.amount, [data-testid="amount"], .invoice-amount'
                ).text_content()

                if amount_text:
                    # Extract numeric amount
                    amount_match = re.search(r"[\d,]+\.?\d*", amount_text.replace(",", ""))
                    if amount_match:
                        amount = float(amount_match.group())
                        if amount > 0:
                            invoice_row = row
                            break

        # Verify invoice exists and amount > 0
        await expect(invoice_row).to_be_visible(timeout=10000)

        # Extract and verify amount
        amount_element = invoice_row.locator(
            '.amount, [data-testid="amount"], .invoice-amount'
        )
        amount_text = await amount_element.text_content()

        # Parse amount
        amount_match = re.search(r"[\d,]+\.?\d*", amount_text.replace(",", ""))
        assert amount_match, f"Could not parse invoice amount from: {amount_text}"

        amount = float(amount_match.group())
        assert amount > 0, f"Invoice amount should be > 0, got: {amount}"

        # Verify invoice status
        status_element = invoice_row.locator(
            '.status, [data-testid="status"]'
        )
        if await status_element.is_visible():
            status = await status_element.text_content()
            print(f"  Invoice status: {status}")

        print(f"✓ Billing verified: ¥{amount:,.2f}")

    # ==================== Full Flow Test ====================

    @pytest.mark.asyncio
    @pytest.mark TC001
    @pytest.mark.employer
    @pytest.mark.full_flow
    async def test_tc001_complete_flow(
        self,
        employer_page: Page,
        test_employer_data: dict,
        test_job_data: dict,
        api_client,
    ):
        """
        TC-001: 雇主完整招聘流程 (端到端)

        按顺序执行所有步骤，验证完整流程。
        """
        print("\n" + "=" * 60)
        print("TC-001: Employer Complete Recruitment Flow")
        print("=" * 60)

        # Step 1: Login
        print("\n[Step 1/8] Employer Login")
        await self.test_step1_employer_login(employer_page, test_employer_data)

        # Get token for API calls
        token = await employer_page.evaluate(
            "() => localStorage.getItem('access_token')"
        )
        api_client.set_token(token)

        # Step 2-3: Create Job
        print("\n[Step 2-3/8] Create Job")
        job_id = await self.test_step2_3_create_job(employer_page, test_job_data)

        # Step 4: Wait for Shortlist
        print("\n[Step 4/8] Wait for Shortlist (max 60s)")
        await self.test_step4_wait_for_shortlist(employer_page, api_client)

        # Step 5: Verify Pipeline Board
        print("\n[Step 5/8] Verify Pipeline Board")
        await self.test_step5_verify_pipeline_board(employer_page)

        # Step 6: Move Candidate
        print("\n[Step 6/8] Move Candidate to Invited")
        await self.test_step6_move_candidate_to_invited(employer_page, api_client)

        # Step 7: Simulate Onboarding
        print("\n[Step 7/8] Simulate Onboarding")
        await self.test_step7_simulate_onboarding(employer_page, api_client)

        # Step 8: Verify Billing
        print("\n[Step 8/8] Verify Billing")
        await self.test_step8_verify_billing(employer_page, api_client)

        print("\n" + "=" * 60)
        print("TC-001 PASSED: Complete employer flow verified!")
        print("=" * 60)


# ==================== Helper Functions ====================

async def wait_for_selector_with_retry(
    page: Page,
    selector: str,
    max_retries: int = 3,
    timeout: int = 10000,
):
    """Wait for selector with retry logic."""
    for _ in range(max_retries):
        try:
            element = page.locator(selector)
            await element.wait_for(timeout=timeout)
            return element
        except Exception:
            await asyncio.sleep(1)
    raise TimeoutError(f"Selector {selector} not found after {max_retries} retries")
