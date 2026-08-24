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
import re
import time
from typing import Any, Iterator
from urllib.parse import quote, unquote

import httpx

from app.core.config import settings
from app.guardrails.runtime import record_audit
from app.observability.trace import record_trace

logger = logging.getLogger("macau_storywalk.qwenpaw")

# 发消息端点（已确认；做成单一配置点，便于将来 QwenPaw 改路由时一处修改）
SEND_PATH_DEFAULT = "/api/console/chat"
_IMAGE_URI_RE = re.compile(
    r"(?:file|https?)://[^\r\n\"\]}]+?\.(?:png|jpe?g|webp)(?:\?[^\s\"\]}]*)?",
    re.IGNORECASE,
)
_SAVED_IMAGE_RE = re.compile(
    r"Saved to:\s*(.+?\.(?:png|jpe?g|webp))(?=\s*(?:$|[,;]))",
    re.IGNORECASE | re.MULTILINE,
)
_AUDIO_URI_RE = re.compile(
    r"(?:file|https?)://[^\r\n\"\]}]+?\.(?:mp3|wav|m4a|ogg)(?:\?[^\s\"\]}]*)?",
    re.IGNORECASE,
)
_SAVED_AUDIO_RE = re.compile(
    r"Saved to:\s*(.+?\.(?:mp3|wav|m4a|ogg))(?=\s*(?:$|[,;]))",
    re.IGNORECASE | re.MULTILINE,
)


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

    def send(
        self,
        session_id: str,
        text: str,
        agent_id: str | None = None,
        *,
        max_duration: float | None = None,
    ) -> dict[str, Any]:
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

        events: list[dict[str, Any]] = []
        deadline = time.perf_counter() + max_duration if max_duration else None
        stream_timeout = min(self.timeout, max_duration) if max_duration else self.timeout
        try:
            with httpx.stream(
                "POST", url, headers=headers, json=payload, timeout=stream_timeout
            ) as resp:
                self._raise_for_status(resp, self.send_path)
                for event in _iter_sse(resp):
                    if deadline is not None and time.perf_counter() >= deadline:
                        raise QwenPawError(
                            f"POST {self.send_path} exceeded {max_duration:.1f}s total duration"
                        )
                    events.append(event)
        except httpx.HTTPError as exc:
            raise QwenPawError(f"POST {self.send_path} 网络失败：{exc}") from exc

        answer = _assemble_answer(events)
        return {"text": answer, "tokens": _extract_usage(events), "session_id": session_id}

    def ask_for_image(
        self,
        agent_id: str,
        text: str,
        *,
        session_id: str,
    ) -> str:
        """Run an agent until its tool emits an image and return that image reference.

        Image tools may leave the agent composing a follow-up message after the
        expensive generation has already completed. This method consumes the SSE
        stream only until an image block appears, then stops that chat explicitly.
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
        headers["X-Agent-Id"] = agent_id
        events: list[dict[str, Any]] = []
        image_ref = ""
        t0 = time.perf_counter()

        try:
            with httpx.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            ) as resp:
                self._raise_for_status(resp, self.send_path)
                for event in _iter_sse(resp):
                    events.append(event)
                    refs = _extract_image_refs(event.get("data_obj"))
                    if refs:
                        image_ref = refs[0]
                        break
        except httpx.HTTPError as exc:
            raise QwenPawError(f"POST {self.send_path} 网络失败：{exc}") from exc

        if image_ref:
            self._stop_chat_for_session(session_id, agent_id)
        else:
            refs = _extract_image_refs(events)
            image_ref = refs[0] if refs else ""
        if not image_ref:
            answer = _assemble_answer(events)
            raise QwenPawError(f"scene agent 未返回图片：{answer[:200]}")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        record_trace(
            kind="qwenpaw.image",
            agent_id=agent_id,
            chat_id=session_id,
            input_summary=text[:200],
            output_summary=image_ref[:200],
            latency_ms=latency_ms,
            tokens=_extract_usage(events),
        )
        record_audit(
            kind="qwenpaw.image",
            status="ok",
            subject=session_id,
            agent_id=agent_id,
            latency_ms=latency_ms,
            input_chars=len(text),
            output_chars=len(image_ref),
        )
        return image_ref

    def ask_for_audio(
        self,
        agent_id: str,
        text: str,
        *,
        session_id: str,
    ) -> str:
        """Run an agent until its mounted TTS tool emits an audio reference."""
        url = f"{self.base_url}{self.send_path}"
        payload = {
            "input": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "session_id": session_id,
            "user_id": "default",
            "channel": "console",
            "stream": True,
        }
        headers = self._headers(json_body=True)
        headers["X-Agent-Id"] = agent_id
        events: list[dict[str, Any]] = []
        audio_ref = ""
        t0 = time.perf_counter()
        try:
            with httpx.stream(
                "POST", url, headers=headers, json=payload, timeout=self.timeout
            ) as resp:
                self._raise_for_status(resp, self.send_path)
                for event in _iter_sse(resp):
                    events.append(event)
                    refs = _extract_audio_refs(event.get("data_obj"))
                    if refs:
                        audio_ref = refs[0]
                        break
        except httpx.HTTPError as exc:
            raise QwenPawError(f"POST {self.send_path} 网络失败：{exc}") from exc

        if audio_ref:
            self._stop_chat_for_session(session_id, agent_id)
        else:
            refs = _extract_audio_refs(events)
            audio_ref = refs[0] if refs else ""
        if not audio_ref:
            answer = _assemble_answer(events)
            raise QwenPawError(f"guide agent 未返回音频：{answer[:200]}")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        record_trace(
            kind="qwenpaw.audio",
            agent_id=agent_id,
            chat_id=session_id,
            input_summary=text[:200],
            output_summary=audio_ref[:200],
            latency_ms=latency_ms,
            tokens=_extract_usage(events),
        )
        record_audit(
            kind="qwenpaw.audio",
            status="ok",
            subject=session_id,
            agent_id=agent_id,
            latency_ms=latency_ms,
            input_chars=len(text),
            output_chars=len(audio_ref),
        )
        return audio_ref

    def download_media(self, reference: str, *, timeout: float = 45.0) -> bytes:
        """Download a QwenPaw-local or HTTP image/audio media reference."""
        external = False
        if reference.lower().startswith("file://"):
            local_path = unquote(reference[len("file://") :]).replace("\\", "/")
            # Canonical Windows file URIs use ``file:///C:/...`` while the
            # QwenPaw plugin also emits ``file://C:\\...``.  Normalize both
            # without removing the leading slash from POSIX/macOS paths.
            if re.match(r"^/[A-Za-z]:/", local_path):
                local_path = local_path[1:]
            encoded_path = quote(local_path, safe="/:")
            url = f"{self.base_url}/api/files/preview/{encoded_path}"
            headers = self._headers()
        elif reference.lower().startswith(("http://", "https://")):
            url = reference
            external = not reference.startswith(self.base_url)
            headers = self._headers() if not external else {}
        else:
            raise QwenPawError("QwenPaw agent 返回了不支持的媒体引用")

        download_urls = [url]
        if external and ".oss-accelerate.aliyuncs.com" in url:
            download_urls.insert(
                0,
                url.replace(
                    ".oss-accelerate.aliyuncs.com",
                    ".oss-cn-wulanchabu.aliyuncs.com",
                ),
            )

        last_error: Exception | None = None
        for download_url in download_urls:
            for attempt in range(3):
                try:
                    response = httpx.get(
                        download_url,
                        headers=headers,
                        timeout=timeout,
                        follow_redirects=True,
                        trust_env=not external,
                    )
                    self._raise_for_status(response, "/api/files/preview")
                    break
                except (httpx.HTTPError, QwenPawError) as exc:
                    last_error = exc
                    if attempt < 2:
                        time.sleep(0.5 * (2**attempt))
            else:
                continue
            break
        else:
            raise QwenPawError(f"下载 QwenPaw agent 媒体失败：{last_error}") from last_error
        if len(response.content) > 20 * 1024 * 1024:
            raise QwenPawError("QwenPaw agent 媒体超过 20 MiB 限制")
        return response.content

    def upload_media(
        self,
        content: bytes,
        *,
        filename: str,
        agent_id: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload scrubbed media to an agent workspace and return its local path."""
        if not content or len(content) > 20 * 1024 * 1024:
            raise QwenPawError("上传到 scene agent 的图片为空或超过 20 MiB")
        headers = self._headers()
        headers["X-Agent-Id"] = agent_id
        try:
            response = httpx.post(
                f"{self.base_url}/api/console/upload",
                headers=headers,
                files={"file": (filename, content, content_type)},
                timeout=min(self.timeout, 30.0),
            )
            self._raise_for_status(response, "/api/console/upload")
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise QwenPawError(f"上传 scene agent 参考图失败：{exc}") from exc
        reference = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(reference, str) or not reference.strip():
            raise QwenPawError("scene agent 上传接口未返回文件路径")
        return reference.strip()

    def _stop_chat_for_session(self, session_id: str, agent_id: str) -> None:
        """Best-effort stop after an image tool result has been captured."""
        headers = self._headers()
        headers["X-Agent-Id"] = agent_id
        try:
            chats = httpx.get(
                f"{self.base_url}/api/chats",
                headers=headers,
                timeout=min(self.timeout, 10.0),
            )
            self._raise_for_status(chats, "/api/chats")
            rows = chats.json()
            if not isinstance(rows, list):
                return
            chat_id = next(
                (
                    str(row.get("id"))
                    for row in rows
                    if isinstance(row, dict) and row.get("session_id") == session_id
                ),
                "",
            )
            if not chat_id:
                return
            response = httpx.post(
                f"{self.base_url}/api/console/chat/stop",
                headers=headers,
                params={"chat_id": chat_id},
                timeout=min(self.timeout, 10.0),
            )
            self._raise_for_status(response, "/api/console/chat/stop")
        except (httpx.HTTPError, QwenPawError, ValueError) as exc:
            logger.info("QwenPaw image chat stop failed: %s", exc)

    def ask(
        self,
        agent_id: str,
        text: str,
        *,
        session_id: str | None = None,
        session_name: str = "harness",
        max_duration: float | None = None,
    ) -> str:
        """高层封装：发消息 → 返回 assistant 最终文本。失败抛 QwenPawError。

        默认每个 agent 复用一个稳定 session_id（``{session_name}-{agent_id}``），
        即同一 agent 的多次调用续同一会话线程；需要隔离时由调用方传 ``session_id``。
        """
        sid = session_id or f"{session_name}-{agent_id}"
        t0 = time.perf_counter()
        result = self.send(sid, text, agent_id=agent_id, max_duration=max_duration)
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
        record_audit(
            kind="qwenpaw.ask",
            status="ok",
            subject=sid,
            agent_id=agent_id,
            latency_ms=latency_ms,
            tokens=result.get("tokens"),
            input_chars=len(text),
            output_chars=len(result.get("text") or ""),
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


def _extract_image_refs(obj: Any) -> list[str]:
    """Find image references, preferring structured tool output over text."""
    structured: list[str] = []
    inline: list[str] = []
    saved: list[str] = []

    def add(bucket: list[str], value: str) -> None:
        cleaned = value.strip().rstrip(".,;)")
        if cleaned and cleaned not in bucket:
            bucket.append(cleaned)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            source = value.get("source")
            if value.get("type") == "image" and isinstance(source, dict):
                url = source.get("url")
                if isinstance(url, str):
                    add(structured, url)
            for child in value.values():
                visit(child)
            return
        if isinstance(value, list):
            for child in value:
                visit(child)
            return
        if isinstance(value, str):
            for match in _IMAGE_URI_RE.finditer(value):
                add(inline, match.group(0))
            for match in _SAVED_IMAGE_RE.finditer(value):
                add(saved, f"file://{match.group(1).strip()}")

    visit(obj)
    found: list[str] = []
    for bucket in (structured, inline, saved):
        bucket.sort(key=lambda ref: not ref.lower().startswith("file://"))
        for ref in bucket:
            if ref not in found:
                found.append(ref)
    return found


def _extract_audio_refs(obj: Any) -> list[str]:
    """Find MP3/WAV references from QwenPaw tool output or response text."""
    inline: list[str] = []
    saved: list[str] = []

    def add(bucket: list[str], value: str) -> None:
        cleaned = value.strip().rstrip(".,;)")
        if cleaned and cleaned not in bucket:
            bucket.append(cleaned)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
            return
        if isinstance(value, list):
            for child in value:
                visit(child)
            return
        if isinstance(value, str):
            for match in _AUDIO_URI_RE.finditer(value):
                add(inline, match.group(0))
            for match in _SAVED_AUDIO_RE.finditer(value):
                add(saved, f"file://{match.group(1).strip()}")

    visit(obj)
    return [*inline, *saved]


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
