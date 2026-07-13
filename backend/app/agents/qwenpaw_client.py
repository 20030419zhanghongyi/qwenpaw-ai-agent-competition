"""QwenPaw 连接基座（P0）。

封装对本地 QwenPaw 实例（默认 http://127.0.0.1:8088，API base `/api`）的调用：
- 只读探测（GET）：version / agents / chats / chat 详情 —— **本机无需鉴权**，ping 用它
- 发消息收回复（POST `/api/console/chat`，SSE）—— agent 由 `X-Agent-Id` 头指定

> **已验证契约**（Console bundle 反编译 + 一次真实调用确认，2026-07-10）：
> POST `/api/console/chat`，body `{input:[{role,content}], session_id, user_id,
> channel:"console", stream:true}`；响应 `text/event-stream`，事件为标准 SSE
> `data: {...}`。流里有两类 message：`type:"reasoning"`（思维链，丢弃）与
> `type:"message"`（最终答复，取这个）；token 用量在末尾 `turn_usage` 事件。
> 全程本机无需鉴权；POST 若上线后 401，再用 `.env` 的 `QWENPAW_AUTH_*` 注入。

设计原则：所有网络/解析失败统一抛 `QwenPawError`，调用方据此降级到规则版，
绝不让 QwenPaw 抖动打穿业务接口。外层 harness 不重建 QwenPaw 内层能力。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterator

import httpx

from app.core.config import settings
from app.observability.trace import record_trace

logger = logging.getLogger("macau_storywalk.qwenpaw")

# 发消息端点（已确认；做成单一配置点，便于将来 QwenPaw 改路由时一处修改）
SEND_PATH_DEFAULT = "/api/console/chat"


class QwenPawError(RuntimeError):
    """QwenPaw 调用失败的统一异常（网络/状态码/解析）。"""


class QwenPawClient:
    """同步 httpx 封装（与现有全同步 FastAPI 代码风格一致）。"""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | None = None,
        auth_cookie: str | None = None,
        auth_header: str | None = None,
        send_path: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.qwenpaw_base_url).rstrip("/")
        self.timeout = settings.qwenpaw_timeout if timeout is None else timeout
        self.send_path = send_path or settings.qwenpaw_send_path_template or SEND_PATH_DEFAULT
        self._auth_cookie = auth_cookie if auth_cookie is not None else settings.qwenpaw_auth_cookie
        self._auth_header = auth_header if auth_header is not None else settings.qwenpaw_auth_header

    # ---- 内部 ----------------------------------------------------------

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self._auth_header:
            key, _, value = self._auth_header.partition(":")
            headers[key.strip() or "Authorization"] = value.strip()
        if self._auth_cookie:
            headers["Cookie"] = self._auth_cookie
        return headers

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        t0 = time.perf_counter()
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise QwenPawError(f"GET {path} 网络失败：{exc}") from exc
        self._raise_for_status(resp, path)
        logger.debug("GET %s %d %.0fms", path, resp.status_code, (time.perf_counter() - t0) * 1000)
        return resp.json()

    def _raise_for_status(self, resp: httpx.Response, path: str) -> None:
        if resp.status_code >= 400:
            # send() 走 httpx.stream，流式响应访问 body 前必须先 read()，
            # 否则 httpx.ResponseNotRead 会把 QwenPaw 的真实错误信息吞掉
            try:
                resp.read()
            except httpx.HTTPError:
                pass
            body = resp.text[:300]
            raise QwenPawError(f"{path} 返回 {resp.status_code}：{body}")

    # ---- 只读探测（ping 用，不触发 LLM）-------------------------------

    def version(self) -> dict[str, Any]:
        """`GET /api/version`，如 {"version": "1.1.12.post3"}。"""
        return self._get("/api/version")

    def list_agents(self) -> list[dict[str, Any]]:
        """`GET /api/agents`，返回 agent 列表（id/name/active_model/enabled）。"""
        data = self._get("/api/agents")
        agents = data.get("agents", []) if isinstance(data, dict) else data
        return agents if isinstance(agents, list) else []

    def list_chats(self) -> list[dict[str, Any]]:
        """`GET /api/chats`，返回会话列表。"""
        data = self._get("/api/chats")
        return data if isinstance(data, list) else []

    def get_chat(self, chat_id: str) -> dict[str, Any]:
        """`GET /api/chats/{id}`，返回详情（含 messages 数组）。"""
        return self._get(f"/api/chats/{chat_id}")

    def ping(self) -> dict[str, Any]:
        """连通性探针：version + agents + default agent 是否存在。"""
        version = self.version()
        agents = self.list_agents()
        agent_ids = {a.get("id") for a in agents}
        default_id = settings.qwenpaw_default_agent_id
        return {
            "reachable": True,
            "qwenpaw_version": version.get("version"),
            "agents": [{"id": a.get("id"), "name": a.get("name")} for a in agents],
            "default_agent": default_id,
            "default_agent_present": default_id in agent_ids,
        }

    # ---- 发消息收回复（LLM 路径）--------------------------------------

    def send(self, session_id: str, text: str, agent_id: str | None = None) -> dict[str, Any]:
        """发一条消息，消费 SSE 流到结束，返回 {text, tokens, session_id}。

        - agent 由 ``X-Agent-Id`` 头指定（默认取 config 的 default agent）
        - ``session_id`` 复用即续同一会话线程；新 id 会被自动建会话
        - 返回的 text 是**最终答复**（已剔除 reasoning 思维链）
        """
        url = f"{self.base_url}{self.send_path}"
        payload = {
            "input": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "session_id": session_id,
            "user_id": "default",
            "channel": "console",
            "stream": True,
        }
        headers = self._headers(json_body=True)
        agent = agent_id or settings.qwenpaw_default_agent_id
        if agent:
            headers["X-Agent-Id"] = agent

        try:
            with httpx.stream("POST", url, headers=headers, json=payload, timeout=self.timeout) as resp:
                self._raise_for_status(resp, self.send_path)
                events = list(_iter_sse(resp))
        except httpx.HTTPError as exc:
            raise QwenPawError(f"POST {self.send_path} 网络失败：{exc}") from exc

        answer = _assemble_answer(events)
        return {"text": answer, "tokens": _extract_usage(events), "session_id": session_id}

    def ask(
        self,
        agent_id: str,
        text: str,
        *,
        session_id: str | None = None,
        session_name: str = "harness",
    ) -> str:
        """高层封装：发消息 → 返回 assistant 最终文本。失败抛 QwenPawError。

        默认每个 agent 复用一个稳定 session_id（``{session_name}-{agent_id}``），
        即同一 agent 的多次调用续同一会话线程；需要隔离时由调用方传 ``session_id``。
        """
        sid = session_id or f"{session_name}-{agent_id}"
        t0 = time.perf_counter()
        result = self.send(sid, text, agent_id=agent_id)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        record_trace(
            kind="qwenpaw.ask",
            agent_id=agent_id,
            chat_id=sid,
            input_summary=text[:200],
            output_summary=(result.get("text") or "")[:200],
            latency_ms=latency_ms,
            tokens=result.get("tokens"),
        )
        return result.get("text", "")


# ---- 解析工具 ----------------------------------------------------------


def _iter_sse(resp: httpx.Response) -> Iterator[dict[str, Any]]:
    """逐个产出 SSE 事件：{event, data, data_obj}。data_obj 为解析失败的 None。"""
    event_name: str | None = None
    data_lines: list[str] = []

    def flush() -> dict[str, Any] | None:
        nonlocal event_name, data_lines
        if not data_lines:
            return None
        raw = "\n".join(data_lines)
        data_obj: Any = None
        try:
            data_obj = json.loads(raw)
        except json.JSONDecodeError:
            data_obj = None
        evt = {"event": event_name or "message", "data": raw, "data_obj": data_obj}
        event_name, data_lines = None, []
        return evt

    for line in resp.iter_lines():
        if line == "":
            evt = flush()
            if evt is not None:
                yield evt
            continue
        if line.startswith(":"):  # SSE 注释
            continue
        if line.startswith("event:"):
            event_name = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip())

    evt = flush()
    if evt is not None:
        yield evt


def _extract_text(obj: Any) -> str:
    """从 OpenAI 兼容 message / 响应对象里抽 assistant 文本。"""
    if not isinstance(obj, dict):
        return ""
    content = obj.get("content")
    if isinstance(content, str):
        return content
    parts: list[str] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                parts.append(item["text"])
    return "".join(parts)


def _assemble_answer(events: list[dict[str, Any]]) -> str:
    """从 SSE 事件里拼出**最终答复**文本（剔除 reasoning 思维链）。

    优先取 status=completed 且 type=message 的整条 message；不行再按 msg_id
    归并 content delta（只取 message 类、不取 reasoning 类）。
    """
    deltas_by_msg: dict[str | None, list[str]] = {}
    answer_msg_ids: set[str | None] = set()
    final_full = ""

    for evt in events:
        d = evt.get("data_obj")
        if not isinstance(d, dict):
            continue
        obj = d.get("object")
        if obj == "message" and d.get("type") == "message":  # 真正答复（排除 reasoning）
            answer_msg_ids.add(d.get("id"))
            if d.get("status") == "completed":
                full = _extract_text(d)
                if full:
                    final_full = full
        if obj == "content" and d.get("type") == "text" and d.get("delta"):
            deltas_by_msg.setdefault(d.get("msg_id"), []).append(d.get("text", ""))

    if final_full:
        return final_full.strip()
    for mid in answer_msg_ids:
        if mid in deltas_by_msg:
            return "".join(deltas_by_msg[mid]).strip()
    return ""


def _extract_usage(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """从末尾 turn_usage 事件抽 token 用量（可能不存在）。"""
    for evt in reversed(events):
        d = evt.get("data_obj")
        if isinstance(d, dict) and d.get("type") == "turn_usage" and isinstance(d.get("usage"), dict):
            return {k: v for k, v in d["usage"].items() if isinstance(v, (int, float))}
    return None


def get_client() -> QwenPawClient:
    """构造一个使用 config 默认值的客户端。"""
    return QwenPawClient()
