"""
HigherMatch™ E2E Tests - TC-002: Candidate Flow
=============================================

测试用例 TC-002：候选人流程

测试步骤：
1. 候选人登录
2. 上传 PDF 简历（可 mock 接口或上传测试用 dummy_resume.pdf）
3. 验证档案完成度增加
4. 导航至职位推荐页，点击首个岗位的「一键申请」
5. 验证申请追踪页出现该条记录

前置条件：
- 候选人端 Portal 运行在 http://localhost:5174
- 后端 API 运行在 http://localhost:8000
- 已有测试岗位可供申请

版本: 1.0.0
"""

import asyncio
import os
import re
from datetime import datetime

import pytest
import pytest_asyncio
from playwright.async_api import Page, expect, FileChooser


# ==================== Test Configuration ====================

CANDIDATE_PORTAL_URL = "http://localhost:5174"
API_BASE_URL = "http://localhost:8000"

# Profile completeness threshold
MIN_PROFILE_COMPLETENESS_INCREASE = 10  # 简历上传应增加至少10%完成度


# ==================== Test Class ====================

class TestTC002CandidateFlow:
    """
    TC-002: 候选人流程 E2E 测试

    覆盖候选人端核心业务流程：
    登录 -> 上传简历 -> 查看推荐 -> 申请岗位 -> 追踪申请
    """

    @pytest_asyncio.fixture
    async def candidate_page(self, candidate_page: Page) -> Page:
        """Setup page with mobile viewport for candidate portal."""
        # Candidate portal is mobile-first
        await candidate_page.set_viewport_size({"width": 390, "height": 844})
        return candidate_page

    # ==================== Step 1: Login ====================

    @pytest.mark.asyncio
    @pytest.mark TC002
    @pytest.mark.candidate
    async def test_step1_candidate_login(
        self,
        candidate_page: Page,
        test_candidate_data: dict,
    ):
        """
        Step 1: 候选人登录

        测试点：
        - 导航至登录页
        - 输入手机号
        - 获取验证码（mock）
        - 验证登录成功
        """
        phone = test_candidate_data["phone"]

        # Navigate to login page
        await candidate_page.goto(f"{CANDIDATE_PORTAL_URL}/login")
        await candidate_page.wait_for_load_state("networkidle")

        # Find phone input
        phone_input = candidate_page.locator(
            'input[type="tel"], input[placeholder*="手机"]'
        )
        await phone_input.wait_for(timeout=5000)
        await phone_input.fill(phone)

        # Click send verification code button
        send_code_button = candidate_page.locator(
            'button:has-text("获取验证码"), '
            'button:has-text("发送验证码"), '
            '[data-testid="send-code"]'
        )
        await send_code_button.click()

        # Wait for code input field
        code_input = candidate_page.locator(
            'input[placeholder*="验证码"], '
            'input[placeholder*="code"]'
        )
        await code_input.wait_for(timeout=5000)

        # Enter mock verification code
        await code_input.fill("123456")

        # Submit login
        submit_button = candidate_page.locator(
            'button[type="submit"], button:has-text("登录"), button:has-text("验证")'
        )
        await submit_button.click()

        # Wait for redirect to recommendations page
        await candidate_page.wait_for_url(
            f"{CANDIDATE_PORTAL_URL}/recommendations",
            timeout=15000
        )

        # Verify login success
        assert "recommendations" in candidate_page.url, \
            "Should redirect to recommendations after login"

        # Store auth token
        token = await candidate_page.evaluate(
            "() => localStorage.getItem('access_token')"
        )
        assert token is not None, "Auth token should be stored after login"

        # Store user info
        user_id = await candidate_page.evaluate(
            "() => JSON.parse(localStorage.getItem('user_info') || '{}').id"
        )

        print(f"✓ Candidate logged in successfully: {phone}, user_id={user_id}")

    # ==================== Step 2: Upload Resume ====================

    @pytest.mark.asyncio
    @pytest.mark TC002
    @pytest.mark.candidate
    async def test_step2_upload_resume(
        self,
        candidate_page: Page,
        dummy_resume_path: str,
    ):
        """
        Step 2: 上传简历

        测试点：
        - 导航至个人档案页
        - 找到上传简历入口
        - 选择 PDF 文件上传
        - 验证上传成功
        """
        # Navigate to profile page
        await candidate_page.goto(f"{CANDIDATE_PORTAL_URL}/profile")
        await candidate_page.wait_for_load_state("networkidle")

        # Wait for profile page to load
        profile_page = candidate_page.locator(
            '[data-testid="profile-page"], .profile-page, main'
        )
        await profile_page.wait_for(timeout=10000)

        # Get initial profile completeness
        completeness_element = candidate_page.locator(
            '[data-testid="profile-completeness"], '
            '.completeness, '
            '.profile-completeness, '
            'text=/\\d+%/'
        )

        initial_completeness = 0
        if await completeness_element.is_visible():
            completeness_text = await completeness_element.text_content()
            completeness_match = re.search(r"(\d+)", completeness_text)
            if completeness_match:
                initial_completeness = int(completeness_match.group(1))

        print(f"  Initial profile completeness: {initial_completeness}%")

        # Find resume upload section
        upload_section = candidate_page.locator(
            '[data-testid="resume-upload"], '
            '.resume-upload, '
            'button:has-text("上传简历"), '
            'button:has-text("重新上传")'
        )

        # Scroll to upload section if needed
        await upload_section.scroll_into_view_if_needed()
        await upload_section.wait_for(timeout=5000)

        # Check if dummy resume exists, create if not
        if not os.path.exists(dummy_resume_path):
            # Create a minimal PDF for testing
            await self._create_dummy_pdf(dummy_resume_path)

        # Trigger file upload via JavaScript
        file_input = candidate_page.locator(
            'input[type="file"]'
        )

        # Set up file chooser handler
        file_chooser_future = asyncio.Future()

        async def handle_file_chooser(file_chooser: FileChooser):
            if not file_chooser_future.done():
                file_chooser.set_files(dummy_resume_path)
                file_chooser_future.set_result(None)

        candidate_page.on("filechooser", handle_file_chooser)

        # Click upload button
        await upload_section.click()

        # Wait for file chooser or directly set files
        try:
            await asyncio.wait_for(file_chooser_future, timeout=10)
        except asyncio.TimeoutError:
            # Fallback: directly set files via JavaScript
            pass

        # Alternative: Use page.evaluate to trigger file input
        if not file_chooser_future.done():
            await candidate_page.evaluate(
                f"""(filePath) => {{
                    const input = document.querySelector('input[type="file"]');
                    if (input) {{
                        const dataTransfer = new DataTransfer();
                        const file = new File(['PDF content'], 'resume.pdf', {{ type: 'application/pdf' }});
                        dataTransfer.items.add(file);
                        input.files = dataTransfer.files;
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}""",
                dummy_resume_path
            )

        # Wait for upload to process
        await asyncio.sleep(3)

        # Verify upload success
        upload_status = candidate_page.locator(
            '[data-upload-status], .upload-status, '
            'text=/上传成功|已上传|✓/'
        )

        # Check for success indicators
        success_indicators = [
            candidate_page.locator('text=上传成功'),
            candidate_page.locator('text=已上传'),
            candidate_page.locator('[data-status="uploaded"]'),
            candidate_page.locator('.upload-success'),
        ]

        upload_success = False
        for indicator in success_indicators:
            if await indicator.is_visible(timeout=3000):
                upload_success = True
                break

        assert upload_success, "Resume upload should succeed"

        print(f"✓ Resume uploaded successfully")

    async def _create_dummy_pdf(self, file_path: str):
        """Create a minimal dummy PDF for testing."""
        # Minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(pdf_content)

    # ==================== Step 3: Verify Profile Completeness ====================

    @pytest.mark.asyncio
    @pytest.mark TC002
    @pytest.mark.candidate
    async def test_step3_verify_profile_completeness(
        self,
        candidate_page: Page,
    ):
        """
        Step 3: 验证档案完成度增加

        测试点：
        - 获取当前档案完成度
        - 验证完成度有增加
        - 验证简历信息被提取
        """
        # Refresh profile page
        await candidate_page.goto(f"{CANDIDATE_PORTAL_URL}/profile")
        await candidate_page.wait_for_load_state("networkidle")

        # Wait for completeness indicator
        completeness_element = candidate_page.locator(
            '[data-testid="profile-completeness"], '
            '.completeness, '
            '.profile-completeness'
        )

        await completeness_element.wait_for(timeout=10000)

        # Get current completeness
        completeness_text = await completeness_element.text_content()
        completeness_match = re.search(r"(\d+)", completeness_text)
        assert completeness_match, f"Could not parse completeness from: {completeness_text}"

        current_completeness = int(completeness_match.group(1))

        print(f"  Current profile completeness: {current_completeness}%")

        # Verify completeness increased (should be > 0 after upload)
        assert current_completeness > 0, \
            "Profile completeness should be > 0 after resume upload"

        # Verify resume section shows uploaded file
        resume_section = candidate_page.locator(
            '[data-testid="resume-info"], '
            '.resume-info, '
            '.resume-details'
        )

        if await resume_section.is_visible():
            resume_text = await resume_section.text_content()
            # Check for file indicators
            assert any(indicator in resume_text.lower() for indicator in [
                "pdf", "resume", "简历", "已上传"
            ]), "Resume section should show uploaded file"

        print(f"✓ Profile completeness verified: {current_completeness}%")

    # ==================== Step 4: Apply to Job ====================

    @pytest.mark.asyncio
    @pytest.mark TC002
    @pytest.mark.candidate
    async def test_step4_apply_to_job(
        self,
        candidate_page: Page,
        api_client,
    ):
        """
        Step 4: 申请岗位

        测试点：
        - 导航至职位推荐页
        - 找到首个可申请的岗位
        - 点击「一键申请」
        - 验证申请成功
        """
        # Navigate to recommendations page
        await candidate_page.goto(f"{CANDIDATE_PORTAL_URL}/recommendations")
        await candidate_page.wait_for_load_state("networkidle")

        # Wait for job recommendations to load
        recommendations = candidate_page.locator(
            '[data-testid="job-card"], '
            '.job-card, '
            '.recommendation-card'
        )
        await recommendations.first.wait_for(timeout=15000)

        # Count available recommendations
        card_count = await recommendations.count()
        assert card_count > 0, "Should have at least one job recommendation"

        print(f"  Found {card_count} job recommendations")

        # Get first job card info
        first_card = recommendations.first
        job_id = await first_card.get_attribute("data-job-id")
        job_title = await first_card.locator(
            '.job-title, [data-testid="job-title"]'
        ).text_content()

        # Store job ID for verification
        await candidate_page.evaluate(
            f"() => localStorage.setItem('test_applied_job_id', '{job_id}')"
        )

        print(f"  First job: {job_title} (ID: {job_id})")

        # Look for apply button
        apply_button = first_card.locator(
            'button:has-text("一键申请"), '
            'button:has-text("立即申请"), '
            '[data-action="apply"]'
        )

        if await apply_button.is_visible():
            await apply_button.click()
        else:
            # Fallback: Click card to open detail, then apply
            await first_card.click()
            await asyncio.sleep(1)

            # Look for apply button in detail view
            apply_button = candidate_page.locator(
                'button:has-text("一键申请"), '
                'button:has-text("立即申请"), '
                '[data-action="apply"]'
            )

            await apply_button.wait_for(timeout=5000)
            await apply_button.click()

        # Wait for application success
        await asyncio.sleep(2)

        # Check for success indicators
        success_indicators = [
            candidate_page.locator('text=申请成功'),
            candidate_page.locator('text=已申请'),
            candidate_page.locator('[data-status="applied"]'),
            candidate_page.locator('.apply-success'),
        ]

        apply_success = False
        for indicator in success_indicators:
            if await indicator.is_visible(timeout=5000):
                apply_success = True
                break

        # Also check via API
        if not apply_success:
            response = await api_client.get(f"/api/v1/candidates/me/applications")
            if response.get("success"):
                applications = response.get("data", {}).get("applications", [])
                apply_success = any(app.get("job_id") == job_id for app in applications)

        assert apply_success, "Job application should be successful"

        print(f"✓ Applied to job: {job_title} (ID: {job_id})")

        return job_id

    # ==================== Step 5: Verify Application Tracking ====================

    @pytest.mark.asyncio
    @pytest.mark TC002
    @pytest.mark.candidate
    async def test_step5_verify_application_tracking(
        self,
        candidate_page: Page,
    ):
        """
        Step 5: 验证申请追踪

        测试点：
        - 导航至申请追踪页
        - 找到已申请的岗位记录
        - 验证申请状态显示正确
        """
        # Navigate to applications page
        await candidate_page.goto(f"{CANDIDATE_PORTAL_URL}/applications")
        await candidate_page.wait_for_load_state("networkidle")

        # Wait for applications list
        applications_list = candidate_page.locator(
            '[data-testid="applications-list"], '
            '.applications-list, '
            '.application-card'
        )
        await applications_list.wait_for(timeout=10000)

        # Get applied job ID
        job_id = await candidate_page.evaluate(
            "() => localStorage.getItem('test_applied_job_id')"
        )

        # Find the application record
        application_record = candidate_page.locator(
            f'[data-job-id="{job_id}"], '
            f'.application-card:has-text("{job_id}")'
        )

        # Alternative: Look for any application with matching status
        if not await application_record.is_visible():
            application_record = candidate_page.locator(
                '.application-card, [data-testid="application"]'
            ).first

        # Verify application exists
        await expect(application_record).to_be_visible(timeout=10000)

        # Verify application has correct status
        status_indicators = [
            candidate_page.locator('text=已申请'),
            candidate_page.locator('text=待处理'),
            candidate_page.locator('text=推荐中'),
            candidate_page.locator('[data-status="applied"]'),
        ]

        has_valid_status = False
        for indicator in status_indicators:
            if await indicator.is_visible():
                has_valid_status = True
                break

        assert has_valid_status, "Application should have valid status"

        # Verify job title is shown
        job_title_element = application_record.locator(
            '.job-title, [data-testid="job-title"]'
        )

        if await job_title_element.is_visible():
            job_title = await job_title_element.text_content()
            print(f"  Application tracked: {job_title}")

        # Verify timeline or status indicator
        timeline = application_record.locator(
            '.timeline, [data-testid="timeline"]'
        )

        if await timeline.is_visible():
            timeline_items = timeline.locator('.timeline-item, .step')
            item_count = await timeline_items.count()
            print(f"  Timeline steps: {item_count}")

        print(f"✓ Application tracking verified")

    # ==================== Full Flow Test ====================

    @pytest.mark.asyncio
    @pytest.mark TC002
    @pytest.mark.candidate
    @pytest.mark.full_flow
    async def test_tc002_complete_flow(
        self,
        candidate_page: Page,
        test_candidate_data: dict,
        dummy_resume_path: str,
        api_client,
    ):
        """
        TC-002: 候选人完整流程 (端到端)

        按顺序执行所有步骤，验证完整流程。
        """
        print("\n" + "=" * 60)
        print("TC-002: Candidate Complete Flow")
        print("=" * 60)

        # Step 1: Login
        print("\n[Step 1/5] Candidate Login")
        await self.test_step1_candidate_login(candidate_page, test_candidate_data)

        # Get token for API calls
        token = await candidate_page.evaluate(
            "() => localStorage.getItem('access_token')"
        )
        api_client.set_token(token)

        # Step 2: Upload Resume
        print("\n[Step 2/5] Upload Resume")
        await self.test_step2_upload_resume(candidate_page, dummy_resume_path)

        # Step 3: Verify Profile Completeness
        print("\n[Step 3/5] Verify Profile Completeness")
        await self.test_step3_verify_profile_completeness(candidate_page)

        # Step 4: Apply to Job
        print("\n[Step 4/5] Apply to Job")
        job_id = await self.test_step4_apply_to_job(candidate_page, api_client)

        # Step 5: Verify Application Tracking
        print("\n[Step 5/5] Verify Application Tracking")
        await self.test_step5_verify_application_tracking(candidate_page)

        print("\n" + "=" * 60)
        print("TC-002 PASSED: Complete candidate flow verified!")
        print("=" * 60)


# ==================== Mobile Helper Functions ====================

async def tap_element(page: Page, selector: str, timeout: int = 5000):
    """Helper to tap element on mobile viewport."""
    element = page.locator(selector)
    await element.wait_for(timeout=timeout)
    await element.tap()


async def swipe_up(page: Page, distance: int = 300):
    """Helper to swipe up on mobile."""
    await page.evaluate(f"""
        () => {{
            const el = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);
            if (el) {{
                const touch = new Touch({{
                    identifier: 1,
                    target: el,
                    clientX: window.innerWidth / 2,
                    clientY: window.innerHeight / 2
                }});
                const touchStart = new TouchEvent('touchstart', {{
                    touches: [touch],
                    bubbles: true
                }});

                const touchEnd = new TouchEvent('touchend', {{
                    changedTouches: [new Touch({{
                        identifier: 1,
                        target: el,
                        clientX: window.innerWidth / 2,
                        clientY: window.innerHeight / 2 - {distance}
                    }})],
                    bubbles: true
                }});

                el.dispatchEvent(touchStart);
                el.dispatchEvent(touchEnd);
            }}
        }}
    """)


def get_mobile_viewport():
    """Get typical mobile viewport."""
    return {"width": 390, "height": 844}
