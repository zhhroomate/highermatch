"""
HigherMatch™ Pipeline Service - WebSocket Connection Manager
===========================================================

实时协作 WebSocket 服务，支持房间级别的消息广播。

功能特性:
- 多客户端连接管理
- 按岗位 (job) 分组的消息广播
- 连接状态追踪
- 心跳检测

版本: 1.0.0
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ClientInfo:
    """WebSocket 客户端信息"""

    client_id: str
    websocket: WebSocket
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_alive: bool = True


class ConnectionManager:
    """
    WebSocket 连接管理器

    支持:
    - 多客户端并发连接
    - 按房间 (job_{job_id}) 广播消息
    - 连接状态追踪
    - 心跳检测

    使用示例:
    ```python
    manager = ConnectionManager()

    # 客户端连接
    await manager.connect(websocket, job_id="job_123", user_id="user_456")

    # 广播消息到特定岗位
    await manager.broadcast_to_job(
        job_id="job_123",
        event="pipeline.updated",
        data={"match_id": "xxx", "to_stage": "interviewing"}
    )

    # 客户端断开
    await manager.disconnect(client_id)
    ```
    """

    def __init__(self):
        """初始化连接管理器"""
        # client_id -> ClientInfo
        self._clients: Dict[str, ClientInfo] = {}

        # job_id -> Set[client_id]
        self._job_rooms: Dict[str, Set[str]] = {}

        # user_id -> Set[client_id] (一个用户可能有多个连接)
        self._user_sessions: Dict[str, Set[str]] = {}

        # 锁，用于并发安全
        self._lock = asyncio.Lock()

        # 心跳检测间隔 (秒)
        self._heartbeat_interval = 30

        # 心跳检测任务
        self._heartbeat_task: Optional[asyncio.Task] = None

        logger.info("ConnectionManager initialized")

    # ==================== 连接管理 ====================

    async def connect(
        self,
        websocket: WebSocket,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        """
        接受 WebSocket 连接并注册

        Args:
            websocket: FastAPI WebSocket 对象
            job_id: 岗位 ID (可选，用于加入房间)
            user_id: 用户 ID (可选)
            role: 用户角色 (可选)

        Returns:
            client_id: 分配的客户端 ID
        """
        await websocket.accept()

        client_id = str(uuid4())[:8]

        async with self._lock:
            # 创建客户端信息
            client_info = ClientInfo(
                client_id=client_id,
                websocket=websocket,
                job_id=job_id,
                user_id=user_id,
                role=role,
            )

            # 注册到客户端字典
            self._clients[client_id] = client_info

            # 加入岗位房间
            if job_id:
                room_name = self._get_room_name(job_id)
                if room_name not in self._job_rooms:
                    self._job_rooms[room_name] = set()
                self._job_rooms[room_name].add(client_id)
                logger.info(f"Client {client_id} joined room: {room_name}")

            # 注册用户会话
            if user_id:
                if user_id not in self._user_sessions:
                    self._user_sessions[user_id] = set()
                self._user_sessions[user_id].add(client_id)

        logger.info(
            f"Client connected: {client_id}, "
            f"job_id={job_id}, user_id={user_id}, role={role}"
        )

        # 发送连接成功消息
        await self._send_personal_message(
            client_id,
            {
                "event": "connected",
                "data": {
                    "client_id": client_id,
                    "job_id": job_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

        # 广播用户加入
        if job_id:
            await self.broadcast_to_job(
                job_id=job_id,
                event="user.joined",
                data={
                    "client_id": client_id,
                    "user_id": user_id,
                    "role": role,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                exclude_client=client_id,
            )

        return client_id

    async def disconnect(self, client_id: str, reason: str = "normal"):
        """
        断开 WebSocket 连接

        Args:
            client_id: 客户端 ID
            reason: 断开原因
        """
        async with self._lock:
            if client_id not in self._clients:
                return

            client = self._clients[client_id]
            job_id = client.job_id

            # 从房间移除
            if job_id:
                room_name = self._get_room_name(job_id)
                if room_name in self._job_rooms:
                    self._job_rooms[room_name].discard(client_id)
                    if not self._job_rooms[room_name]:
                        del self._job_rooms[room_name]

            # 从用户会话移除
            if client.user_id and client.user_id in self._user_sessions:
                self._user_sessions[client.user_id].discard(client_id)
                if not self._user_sessions[client.user_id]:
                    del self._user_sessions[client.user_id]

            # 标记为不活跃
            client.is_alive = False

            # 从客户端字典移除
            del self._clients[client_id]

        logger.info(
            f"Client disconnected: {client_id}, reason={reason}, job_id={job_id}"
        )

        # 广播用户离开
        if job_id:
            await self.broadcast_to_job(
                job_id=job_id,
                event="user.left",
                data={
                    "client_id": client_id,
                    "user_id": client.user_id,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                exclude_client=client_id,
            )

    async def reconnect(
        self,
        old_client_id: str,
        websocket: WebSocket,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        """
        重新连接 (保持同一用户会话)

        Args:
            old_client_id: 旧客户端 ID
            websocket: 新的 WebSocket 连接
            job_id: 岗位 ID
            user_id: 用户 ID
            role: 用户角色

        Returns:
            新客户端 ID
        """
        # 先断开旧连接
        await self.disconnect(old_client_id, reason="reconnect")

        # 建立新连接
        return await self.connect(
            websocket=websocket,
            job_id=job_id,
            user_id=user_id,
            role=role,
        )

    # ==================== 消息发送 ====================

    async def _send_personal_message(self, client_id: str, message: dict) -> bool:
        """
        发送个人消息

        Args:
            client_id: 客户端 ID
            message: 消息内容

        Returns:
            是否发送成功
        """
        async with self._lock:
            if client_id not in self._clients:
                return False

            client = self._clients[client_id]

        try:
            await client.websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to {client_id}: {e}")
            await self.disconnect(client_id, reason="send_error")
            return False

    async def broadcast_to_job(
        self,
        job_id: str,
        event: str,
        data: dict,
        exclude_client: Optional[str] = None,
    ) -> int:
        """
        广播消息到指定岗位房间的所有客户端

        Args:
            job_id: 岗位 ID
            event: 事件类型
            data: 事件数据
            exclude_client: 要排除的客户端 ID (可选)

        Returns:
            发送成功的客户端数量
        """
        room_name = self._get_room_name(job_id)

        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "room": room_name,
        }

        success_count = 0
        failed_clients = []

        async with self._lock:
            client_ids = list(self._job_rooms.get(room_name, set()))

        for client_id in client_ids:
            if client_id == exclude_client:
                continue

            sent = await self._send_personal_message(client_id, message)
            if sent:
                success_count += 1
            else:
                failed_clients.append(client_id)

        # 清理失败的客户端
        for client_id in failed_clients:
            await self.disconnect(client_id, reason="broadcast_failed")

        logger.info(
            f"Broadcast to {room_name}: event={event}, "
            f"success={success_count}, failed={len(failed_clients)}"
        )

        return success_count

    async def broadcast_to_all(
        self,
        event: str,
        data: dict,
        exclude_client: Optional[str] = None,
    ) -> int:
        """
        广播消息到所有已连接客户端

        Args:
            event: 事件类型
            data: 事件数据
            exclude_client: 要排除的客户端 ID (可选)

        Returns:
            发送成功的客户端数量
        """
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        success_count = 0
        failed_clients = []

        async with self._lock:
            client_ids = list(self._clients.keys())

        for client_id in client_ids:
            if client_id == exclude_client:
                continue

            sent = await self._send_personal_message(client_id, message)
            if sent:
                success_count += 1
            else:
                failed_clients.append(client_id)

        for client_id in failed_clients:
            await self.disconnect(client_id, reason="broadcast_failed")

        return success_count

    async def send_to_user(
        self,
        user_id: str,
        event: str,
        data: dict,
    ) -> int:
        """
        发送消息到指定用户的所有连接

        Args:
            user_id: 用户 ID
            event: 事件类型
            data: 事件数据

        Returns:
            发送成功的连接数量
        """
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        success_count = 0

        async with self._lock:
            client_ids = list(self._user_sessions.get(user_id, set()))

        for client_id in client_ids:
            sent = await self._send_personal_message(client_id, message)
            if sent:
                success_count += 1

        return success_count

    # ==================== 房间管理 ====================

    @staticmethod
    def _get_room_name(job_id: str) -> str:
        """获取房间名称"""
        return f"job_{job_id}"

    async def join_room(self, client_id: str, job_id: str) -> bool:
        """
        将客户端加入房间

        Args:
            client_id: 客户端 ID
            job_id: 岗位 ID

        Returns:
            是否成功
        """
        async with self._lock:
            if client_id not in self._clients:
                return False

            old_room = None
            if self._clients[client_id].job_id:
                old_room = self._get_room_name(self._clients[client_id].job_id)

            new_room = self._get_room_name(job_id)

            # 从旧房间移除
            if old_room and old_room in self._job_rooms:
                self._job_rooms[old_room].discard(client_id)

            # 加入新房间
            if new_room not in self._job_rooms:
                self._job_rooms[new_room] = set()
            self._job_rooms[new_room].add(client_id)

            # 更新客户端信息
            self._clients[client_id].job_id = job_id

        logger.info(f"Client {client_id} joined room: {new_room}")

        # 发送加入成功消息
        await self._send_personal_message(
            client_id,
            {
                "event": "room.joined",
                "data": {
                    "room": new_room,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

        return True

    async def leave_room(self, client_id: str, job_id: str) -> bool:
        """
        将客户端从房间移除

        Args:
            client_id: 客户端 ID
            job_id: 岗位 ID

        Returns:
            是否成功
        """
        room_name = self._get_room_name(job_id)

        async with self._lock:
            if client_id not in self._clients:
                return False

            if room_name in self._job_rooms:
                self._job_rooms[room_name].discard(client_id)

            self._clients[client_id].job_id = None

        logger.info(f"Client {client_id} left room: {room_name}")

        await self._send_personal_message(
            client_id,
            {
                "event": "room.left",
                "data": {
                    "room": room_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

        return True

    # ==================== 状态查询 ====================

    async def get_room_clients(self, job_id: str) -> List[dict]:
        """
        获取房间内的客户端列表

        Args:
            job_id: 岗位 ID

        Returns:
            客户端信息列表
        """
        room_name = self._get_room_name(job_id)

        async with self._lock:
            client_ids = list(self._job_rooms.get(room_name, set()))
            clients = []

            for client_id in client_ids:
                if client_id in self._clients:
                    client = self._clients[client_id]
                    clients.append({
                        "client_id": client.client_id,
                        "user_id": client.user_id,
                        "role": client.role,
                        "connected_at": client.connected_at.isoformat(),
                    })

        return clients

    async def get_stats(self) -> dict:
        """
        获取连接统计信息

        Returns:
            统计信息字典
        """
        async with self._lock:
            return {
                "total_connections": len(self._clients),
                "active_rooms": len(self._job_rooms),
                "active_users": len(self._user_sessions),
                "rooms": {
                    room: len(clients)
                    for room, clients in self._job_rooms.items()
                },
            }

    # ==================== 心跳检测 ====================

    async def start_heartbeat(self):
        """启动心跳检测任务"""
        if self._heartbeat_task is not None:
            return

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Heartbeat task started")

    async def stop_heartbeat(self):
        """停止心跳检测任务"""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat task stopped")

    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self._check_dead_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _check_dead_connections(self):
        """检查并清理断开的连接"""
        now = datetime.now(timezone.utc)
        dead_clients = []

        async with self._lock:
            for client_id, client in self._clients.items():
                # 检查 WebSocket 连接是否活跃
                if not client.is_alive:
                    dead_clients.append(client_id)
                    continue

                # 检查心跳超时
                time_since_heartbeat = (now - client.last_heartbeat).total_seconds()
                if time_since_heartbeat > self._heartbeat_interval * 3:
                    logger.warning(
                        f"Client {client_id} heartbeat timeout "
                        f"({time_since_heartbeat:.1f}s)"
                    )
                    dead_clients.append(client_id)

        for client_id in dead_clients:
            await self.disconnect(client_id, reason="heartbeat_timeout")

    async def receive_ping(self, client_id: str):
        """
        处理客户端的心跳响应

        Args:
            client_id: 客户端 ID
        """
        async with self._lock:
            if client_id in self._clients:
                self._clients[client_id].last_heartbeat = datetime.now(timezone.utc)

        await self._send_personal_message(
            client_id,
            {"event": "pong", "data": {"timestamp": datetime.now(timezone.utc).isoformat()}},
        )

    # ==================== 业务事件广播 ====================

    async def broadcast_pipeline_update(
        self,
        job_id: str,
        match_id: str,
        to_stage: str,
        operator_id: Optional[str] = None,
    ) -> int:
        """
        广播管道更新事件

        当候选人阶段移动时调用此方法通知所有订阅的客户端。

        Args:
            job_id: 岗位 ID
            match_id: 匹配记录 ID
            to_stage: 目标阶段
            operator_id: 操作者 ID (可选)

        Returns:
            发送成功的客户端数量
        """
        return await self.broadcast_to_job(
            job_id=job_id,
            event="pipeline.updated",
            data={
                "match_id": match_id,
                "to_stage": to_stage,
                "operator_id": operator_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_candidate_added(
        self,
        job_id: str,
        match_id: str,
        candidate_name: str,
        score: float,
        operator_id: Optional[str] = None,
    ) -> int:
        """
        广播新候选人加入事件

        Args:
            job_id: 岗位 ID
            match_id: 匹配记录 ID
            candidate_name: 候选人姓名
            score: 匹配分数
            operator_id: 操作者 ID (可选)

        Returns:
            发送成功的客户端数量
        """
        return await self.broadcast_to_job(
            job_id=job_id,
            event="candidate.added",
            data={
                "match_id": match_id,
                "candidate_name": candidate_name,
                "score": score,
                "operator_id": operator_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_candidate_removed(
        self,
        job_id: str,
        match_id: str,
        reason: str = "rejected",
        operator_id: Optional[str] = None,
    ) -> int:
        """
        广播候选人移除事件

        Args:
            job_id: 岗位 ID
            match_id: 匹配记录 ID
            reason: 移除原因
            operator_id: 操作者 ID (可选)

        Returns:
            发送成功的客户端数量
        """
        return await self.broadcast_to_job(
            job_id=job_id,
            event="candidate.removed",
            data={
                "match_id": match_id,
                "reason": reason,
                "operator_id": operator_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


# ==================== 单例实例 ====================

# 全局 WebSocket 连接管理器实例
websocket_manager: Optional[ConnectionManager] = None


def get_websocket_manager() -> ConnectionManager:
    """获取 WebSocket 管理器单例"""
    global websocket_manager
    if websocket_manager is None:
        websocket_manager = ConnectionManager()
    return websocket_manager


# ==================== 导出 ====================

__all__ = [
    "ConnectionManager",
    "ClientInfo",
    "websocket_manager",
    "get_websocket_manager",
]
