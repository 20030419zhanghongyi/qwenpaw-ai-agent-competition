"""全局配置：从仓库根目录的 .env 文件读取。

优先级：进程环境变量 > .env 文件 > 代码默认值。
.env 由 .gitignore 忽略，请勿提交真实 key。
"""

from functools import lru_cache
from pathlib import Path
import sys as _sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> 向上 3 层到仓库根
REPO_ROOT = Path(__file__).resolve().parents[3]

# 让 backend 能 import 仓库根下的 rag/（RAG 模块在仓库根、不在 backend/app 内）。
# config 被几乎所有模块早 import，放在这里保证 rag 可用。
if str(REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(REPO_ROOT))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 运行环境
    app_env: str = "dev"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    # QwenPaw / 百炼 / DashScope
    dashscope_api_key: str = ""
    # RAG 向量检索专用 key（text-embedding-v3 走百炼/DashScope）；
    # 独立填写便于单独控量/换号；留空时代码回落到 dashscope_api_key。
    qwen_embedding_api_key: str = ""
    qwenpaw_app_id: str = ""
    qwenpaw_api_key: str = ""
    qwen_text_model: str = "qwen-plus"

    # QwenPaw 外层 harness 连接（P0 连接基座）
    # 实例已在 http://127.0.0.1:8088 跑；本机 GET 无需鉴权，POST 可能需 web token。
    qwenpaw_base_url: str = "http://127.0.0.1:8088"
    qwenpaw_timeout: float = 60.0
    qwenpaw_default_agent_id: str = "default"
    # 发消息端点：已确认 POST /api/console/chat（SSE，agent 由 X-Agent-Id 头指定）
    qwenpaw_send_path_template: str = "/api/console/chat"
    # 可选鉴权：POST 若 401，从 Console devtools 抓 Cookie / Authorization 填这里
    qwenpaw_auth_cookie: str = ""
    qwenpaw_auth_header: str = ""
    # P1 路线 agent 开关：默认 False（规则版 fallback，零意外 LLM 调用）；
    # 在 QwenPaw 建好 route agent 后置 true。
    route_agent_enabled: bool = False
    # 需求理解 agent 开关：默认 False（规则版 fallback，零意外 LLM 调用）；
    # 在 QwenPaw 建好 intent agent 后置 true。
    intent_agent_enabled: bool = False
    # 偏好多轮引导 agent 开关：默认 False（脚本版 fallback，零意外 LLM 调用）；
    # 在 QwenPaw 建好 pref-guide agent（挂 preference-guide 技能）后置 true。
    preference_guide_agent_enabled: bool = False
    # Phase 4 拍照识别开关：默认 False（零意外 agent 调用）。
    # 需在 QwenPaw 建 photo agent（多模态模型 + view_image 工具 + photo-recognize 技能）后置 true。
    photo_agent_enabled: bool = False
    # 文化讲解 agent 开关：默认 False（讲解字段 explanation 留空）。
    # 需在 QwenPaw 建 guide agent（挂 macau-guide 技能）+ RAG 已 ingest 后置 true。
    guide_agent_enabled: bool = False
    # 独立审核 agent 开关：默认 False（规则版 fallback，零意外 LLM 调用）；
    # 在 QwenPaw 建好 reviewer agent（挂 content-safety-review 技能）后置 true。
    reviewer_agent_enabled: bool = False
    # 明信片场景插画 agent id（批量脚本默认调用；需多模态 + view_image + postcard-scene）。
    scene_agent_id: str = "scene"
    qwen_vision_model: str = "qwen-vl-max"
    qwen_embedding_model: str = "text-embedding-v3"
    qwen_tts_model: str = "qwen3-tts-flash"

    # 高德地图
    amap_api_key: str = ""
    amap_web_service_key: str = ""
    amap_security_code: str = ""

    # 数据库 / 向量库
    database_url: str = (
        "postgresql+psycopg://qwenpaw:qwenpaw_dev_password@127.0.0.1:5432/qwenpaw"
    )
    db_echo: bool = False
    pgvector_enabled: bool = Field(default=False)

    # 认证
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 10080

    # 外部数据（Phase 4 可选）
    weather_api_key: str = ""
    crowd_api_key: str = ""
    tts_api_key: str = ""

    postcard_ai_image_enabled: bool = True
    qwen_image_model: str = "wanx2.1-t2i-turbo"
    postcard_ai_image_size: str = "2368*1728"
    # Slightly above the Qwen-Image tool timeout; then fall back to local scenic.
    postcard_ai_scene_timeout: float = 210.0
    # Optional AI caption via guide agent (off by default — keeps create snappy).
    postcard_ai_caption_enabled: bool = False

    # 阿里云 OSS（TTS 私有音频对象）
    oss_endpoint: str = ""
    oss_region: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_audio_prefix: str = "tts"
    oss_signed_url_ttl_seconds: int = 3600

    # 大麦／票务：无公开免费 API。淘宝开放平台 alibaba.damai.* 需合作方 AppKey，暂不接入。
    # damai_app_key: str = ""
    # damai_app_secret: str = ""

    # Guardrails / audit
    audit_hash_salt: str = ""
    audit_retention_days: int = 30
    model_version: str = "qwenpaw-managed"
    prompt_version: str = "ethics-v1"

    # Seed / cache data root (override in tests via monkeypatch or DATA_DIR).
    data_dir: Path = REPO_ROOT / "data"

    @property
    def repo_root(self) -> Path:
        return REPO_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
