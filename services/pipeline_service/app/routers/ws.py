"""
HigherMatch™ Pipeline Service - WebSocket Router
===============================================

WebSocket 实时协作路由，支持候选人管道看板的实时同步。

WebSocket 端点:
- ws://{host}/api/v1/ws/pipeline/{job_id}

事件:
- pipeline.updated: 候选人阶段更新
- candidate.added: 新候选人加入
- candidate.removed: 候选人移除
- user.joined: 用户加入
- user.left: 用户离开

版本: 1.0.0
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.websocket import get_websocket_manager, ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/v1/ws/pipeline/{job_id}")
async def websocket_pipeline(
    websocket: WebSocket,
    job_id: str,
    token: Optional[str] = Query(None, description="JWT Token for authentication"),
):
    """
    候选人管道 WebSocket 连接

    连接后自动加入对应岗位的房间，接收该岗位的所有实时更新。

    **URL**: ws://{host}/api/v1/ws/pipeline/{job_id}

    **认证**:
    - 可通过 query 参数 `token` 传递 JWT
    - 连接成功后会验证 token 并获取用户信息

    **示例**:
    ```javascript
    const ws = new WebSocket(
        'ws://localhost:8003/api/v1/ws/pipeline/job_123?token=xxx'
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === 'pipeline.updated') {
            console.log('Pipeline updated:', data.data);
        }
    };
    ```

    **事件列表**:
    - `connected`: 连接成功
    - `pipeline.updated`: 候选人阶段移动
    - `candidate.added`: 新候选人加入
    - `candidate.removed`: 候选人移除
    - `user.joined`: 用户加入房间
    - `user.left`: 用户离开房间
    - `error`: 错误通知
    """
    manager = get_websocket_manager()

    # 解析用户信息 (可选)
    user_id = None
    role = None

    if token:
        try:
            from jose import jwt, JWTError

            JWT_SECRET_KEY = "your-secret-key-change-in-production"
            JWT_ALGORITHM = "HS256"

            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            role = payload.get("role")

            logger.info(f"WebSocket auth: user_id={user_id}, role={role}")

        except JWTError as e:
            logger.warning(f"WebSocket token validation failed: {e}")
            # 继续连接，但不关联用户

    # 接受连接
    client_id = await manager.connect(
        websocket=websocket,
        job_id=job_id,
        user_id=user_id,
        role=role,
    )

    logger.info(f"WebSocket connected: client_id={client_id}, job_id={job_id}")

    try:
        # 启动心跳
        await manager.start_heartbeat()

        # 消息循环
        while True:
            try:
                # 接收消息
                raw_message = await websocket.receive_text()

                # 解析消息
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    await manager._send_personal_message(
                        client_id,
                        {
                            "event": "error",
                            "data": {
                                "code": "INVALID_JSON",
                                "message": "Invalid JSON format",
                            },
                        },
                    )
                    continue

                # 处理消息类型
                await handle_client_message(manager, client_id, job_id, message)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: client_id={client_id}")
                break

            except Exception as e:
                logger.error(f"WebSocket message error: {e}", exc_info=True)
                await manager._send_personal_message(
                    client_id,
                    {
                        "event": "error",
                        "data": {
                            "code": "MESSAGE_ERROR",
                            "message": str(e),
                        },
                    },
                )

    finally:
        # 断开连接
        await manager.disconnect(client_id, reason="connection_closed")
        logger.info(f"WebSocket cleanup: client_id={client_id}")


async def handle_client_message(
    manager: ConnectionManager,
    client_id: str,
    job_id: str,
    message: dict,
) -> None:
    """
    处理客户端消息

    支持的消息类型:
    - ping: 心跳响应
    - join_room: 加入房间
    - leave_room: 离开房间
    - get_stats: 获取统计信息
    - get_clients: 获取房间内客户端列表
    """
    msg_type = message.get("type")
    data = message.get("data", {})

    switch = {
        "ping": lambda: handle_ping(manager, client_id),
        "join_room": lambda: handle_join_room(manager, client_id, data),
        "leave_room": lambda: handle_leave_room(manager, client_id, data),
        "get_stats": lambda: handle_get_stats(manager, client_id),
        "get_clients": lambda: handle_get_clients(manager, client_id, job_id),
    }

    handler = switch.get(msg_type)
    if handler:
        await handler()
    else:
        await manager._send_personal_message(
            client_id,
            {
                "event": "error",
                "data": {
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"Unknown message type: {msg_type}",
                },
            },
        )


async def handle_ping(manager: ConnectionManager, client_id: str):
    """处理心跳"""
    await manager.receive_ping(client_id)


async def handle_join_room(manager: ConnectionManager, client_id: str, data: dict):
    """处理加入房间请求"""
    target_job_id = data.get("job_id")
    if not target_job_id:
        await manager._send_personal_message(
            client_id,
            {
                "event": "error",
                "data": {
                    "code": "MISSING_JOB_ID",
                    "message": "job_id is required",
                },
            },
        )
        return

    success = await manager.join_room(client_id, target_job_id)

    if not success:
        await manager._send_personal_message(
            client_id,
            {
                "event": "error",
                "data": {
                    "code": "JOIN_ROOM_FAILED",
                    "message": "Failed to join room",
                },
            },
        )


async def handle_leave_room(manager: ConnectionManager, client_id: str, data: dict):
    """处理离开房间请求"""
    target_job_id = data.get("job_id")
    if not target_job_id:
        await manager._send_personal_message(
            client_id,
            {
                "event": "error",
                "data": {
                    "code": "MISSING_JOB_ID",
                    "message": "job_id is required",
                },
            },
        )
        return

    success = await manager.leave_room(client_id, target_job_id)

    if not success:
        await manager._send_personal_message(
            client_id,
            {
                "event": "error",
                "data": {
                    "code": "LEAVE_ROOM_FAILED",
                    "message": "Failed to leave room",
                },
            },
        )


async def handle_get_stats(manager: ConnectionManager, client_id: str):
    """处理获取统计信息请求"""
    stats = await manager.get_stats()

    await manager._send_personal_message(
        client_id,
        {
            "event": "stats",
            "data": stats,
        },
    )


async def handle_get_clients(manager: ConnectionManager, client_id: str, job_id: str):
    """处理获取房间客户端列表请求"""
    clients = await manager.get_room_clients(job_id)

    await manager._send_personal_message(
        client_id,
        {
            "event": "room_clients",
            "data": {
                "room": f"job_{job_id}",
                "clients": clients,
            },
        },
    )


# ==================== 导出 ====================

__all__ = ["router"]
