"""
HigherMatch™ Pipeline Service - WebSocket Tests
==============================================

测试 WebSocket 连接管理和消息广播功能。

版本: 1.0.0
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.websocket import (
    ConnectionManager,
    ClientInfo,
    get_websocket_manager,
)


# ==================== ConnectionManager Tests ====================

class TestConnectionManager:
    """测试 ConnectionManager 类"""

    @pytest.fixture
    def manager(self):
        """创建 ConnectionManager 实例"""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟的 WebSocket"""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_creates_client(self, manager, mock_websocket):
        """测试连接创建客户端"""
        client_id = await manager.connect(
            websocket=mock_websocket,
            job_id="job_123",
            user_id="user_456",
            role="employer",
        )

        # 验证
        assert client_id is not None
        assert len(client_id) == 8
        mock_websocket.accept.assert_called_once()

        # 验证客户端已注册
        stats = await manager.get_stats()
        assert stats["total_connections"] == 1

    @pytest.mark.asyncio
    async def test_connect_without_job(self, manager, mock_websocket):
        """测试不指定岗位的连接"""
        client_id = await manager.connect(
            websocket=mock_websocket,
            user_id="user_456",
        )

        assert client_id is not None

        # 验证未加入任何房间
        stats = await manager.get_stats()
        assert stats["active_rooms"] == 0

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self, manager, mock_websocket):
        """测试断开连接移除客户端"""
        client_id = await manager.connect(
            websocket=mock_websocket,
            job_id="job_123",
        )

        await manager.disconnect(client_id)

        # 验证客户端已移除
        stats = await manager.get_stats()
        assert stats["total_connections"] == 0

    @pytest.mark.asyncio
    async def test_join_room(self, manager, mock_websocket):
        """测试加入房间"""
        client_id = await manager.connect(
            websocket=mock_websocket,
        )

        success = await manager.join_room(client_id, "job_123")

        assert success is True

        # 验证客户端在房间中
        clients = await manager.get_room_clients("job_123")
        assert len(clients) == 1
        assert clients[0]["client_id"] == client_id

    @pytest.mark.asyncio
    async def test_leave_room(self, manager, mock_websocket):
        """测试离开房间"""
        client_id = await manager.connect(
            websocket=mock_websocket,
            job_id="job_123",
        )

        success = await manager.leave_room(client_id, "job_123")

        assert success is True

        # 验证客户端已离开房间
        clients = await manager.get_room_clients("job_123")
        assert len(clients) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_job(self, manager, mock_websocket):
        """测试向岗位房间广播"""
        client_id = await manager.connect(
            websocket=mock_websocket,
            job_id="job_123",
        )

        count = await manager.broadcast_to_job(
            job_id="job_123",
            event="pipeline.updated",
            data={"match_id": "test", "to_stage": "interviewing"},
        )

        assert count == 1
        mock_websocket.send_json.assert_called_once()

        # 验证消息格式
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event"] == "pipeline.updated"
        assert call_args["data"]["match_id"] == "test"
        assert call_args["data"]["to_stage"] == "interviewing"

    @pytest.mark.asyncio
    async def test_broadcast_excludes_client(self, manager, mock_websocket):
        """测试广播排除特定客户端"""
        client_id = await manager.connect(
            websocket=mock_websocket,
            job_id="job_123",
        )

        count = await manager.broadcast_to_job(
            job_id="job_123",
            event="test",
            data={},
            exclude_client=client_id,
        )

        assert count == 0
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_pipeline_update(self, manager, mock_websocket):
        """测试广播管道更新事件"""
        await manager.connect(
            websocket=mock_websocket,
            job_id="job_123",
        )

        count = await manager.broadcast_pipeline_update(
            job_id="job_123",
            match_id="match_456",
            to_stage="interviewing",
            operator_id="user_789",
        )

        assert count == 1

        # 验证消息
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event"] == "pipeline.updated"
        assert call_args["data"]["match_id"] == "match_456"
        assert call_args["data"]["to_stage"] == "interviewing"
        assert call_args["data"]["operator_id"] == "user_789"

    @pytest.mark.asyncio
    async def test_get_room_name(self, manager):
        """测试房间名称生成"""
        room_name = manager._get_room_name("job_123")
        assert room_name == "job_job_123"

    @pytest.mark.asyncio
    async def test_stats(self, manager, mock_websocket):
        """测试统计信息"""
        await manager.connect(websocket=mock_websocket, job_id="job_1")
        await manager.connect(websocket=mock_websocket, job_id="job_2")
        await manager.connect(websocket=mock_websocket, job_id="job_1")

        stats = await manager.get_stats()

        assert stats["total_connections"] == 3
        assert stats["active_rooms"] == 2
        assert stats["rooms"]["job_job_1"] == 2
        assert stats["rooms"]["job_job_2"] == 1

    @pytest.mark.asyncio
    async def test_multiple_connections_same_job(self, manager):
        """测试同一岗位的多个连接"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(websocket=ws1, job_id="job_123")
        await manager.connect(websocket=ws2, job_id="job_123")

        clients = await manager.get_room_clients("job_123")
        assert len(clients) == 2

        # 广播应发送到两个客户端
        count = await manager.broadcast_to_job(
            job_id="job_123",
            event="test",
            data={},
        )
        assert count == 2


# ==================== ClientInfo Tests ====================

class TestClientInfo:
    """测试 ClientInfo 数据类"""

    def test_client_info_creation(self):
        """测试客户端信息创建"""
        ws = MagicMock()
        client = ClientInfo(
            client_id="test123",
            websocket=ws,
            job_id="job_456",
            user_id="user_789",
            role="employer",
        )

        assert client.client_id == "test123"
        assert client.websocket == ws
        assert client.job_id == "job_456"
        assert client.user_id == "user_789"
        assert client.role == "employer"
        assert client.is_alive is True
        assert client.connected_at is not None

    def test_client_info_default_values(self):
        """测试默认值"""
        ws = MagicMock()
        client = ClientInfo(client_id="test", websocket=ws)

        assert client.job_id is None
        assert client.user_id is None
        assert client.role is None
        assert client.is_alive is True


# ==================== Singleton Tests ====================

class TestSingleton:
    """测试单例模式"""

    def test_get_websocket_manager_returns_same_instance(self):
        """测试获取同一实例"""
        import app.services.websocket as ws_module

        # 重置单例
        ws_module.websocket_manager = None

        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()

        assert manager1 is manager2


# ==================== Event Format Tests ====================

class TestEventFormat:
    """测试事件格式"""

    @pytest.mark.asyncio
    async def test_pipeline_updated_event_format(self):
        """测试 pipeline.updated 事件格式"""
        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(websocket=ws, job_id="job_123")

        await manager.broadcast_pipeline_update(
            job_id="job_123",
            match_id="match_abc",
            to_stage="interviewing",
            operator_id="user_xyz",
        )

        call_args = ws.send_json.call_args[0][0]

        # 验证必需字段
        assert "event" in call_args
        assert "data" in call_args
        assert "timestamp" in call_args
        assert "room" in call_args

        # 验证字段值
        assert call_args["event"] == "pipeline.updated"
        assert call_args["room"] == "job_job_123"
        assert call_args["data"]["match_id"] == "match_abc"
        assert call_args["data"]["to_stage"] == "interviewing"

        # 验证时间戳格式
        datetime.fromisoformat(call_args["timestamp"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_candidate_added_event_format(self):
        """测试 candidate.added 事件格式"""
        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(websocket=ws, job_id="job_123")

        await manager.broadcast_candidate_added(
            job_id="job_123",
            match_id="match_new",
            candidate_name="张三",
            score=0.95,
        )

        call_args = ws.send_json.call_args[0][0]

        assert call_args["event"] == "candidate.added"
        assert call_args["data"]["match_id"] == "match_new"
        assert call_args["data"]["candidate_name"] == "张三"
        assert call_args["data"]["score"] == 0.95


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client(self):
        """测试断开不存在的客户端"""
        manager = ConnectionManager()

        # 不应抛出异常
        await manager.disconnect("nonexistent")

    @pytest.mark.asyncio
    async def test_join_room_nonexistent_client(self):
        """测试为不存在的客户端加入房间"""
        manager = ConnectionManager()

        success = await manager.join_room("nonexistent", "job_123")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_room_clients_empty_room(self):
        """测试获取空房间的客户端"""
        manager = ConnectionManager()

        clients = await manager.get_room_clients("nonexistent_job")
        assert clients == []
