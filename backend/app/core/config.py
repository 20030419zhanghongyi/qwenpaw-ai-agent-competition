"""全局配置：从仓库根目录的 .env 文件读取。

优先级：进程环境变量 > .env 文件 > 代码默认值。
.env 由 .gitignore 忽略，请勿提交真实 key。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> 向上 3 层到仓库根
REPO_ROOT = Path(__file__).resolve().parents[3]


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
    qwenpaw_app_id: str = ""
    qwenpaw_api_key: str = ""
    qwen_text_model: str = "qwen-plus"
    qwen_vision_model: str = "qwen-vl-max"
    qwen_embedding_model: str = "text-embedding-v3"
    qwen_tts_model: str = "cosyvoice-v1"

    # 高德地图
    amap_api_key: str = ""
    amap_web_service_key: str = ""
    amap_security_code: str = ""

    # 数据库 / 向量库
    database_url: str = "postgresql+psycopg://macau:macau@localhost:5432/macau"
    pgvector_enabled: bool = Field(default=False)

    # 认证
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 10080

    # 外部数据（Phase 4 可选）
    weather_api_key: str = ""
    crowd_api_key: str = ""
    tts_api_key: str = ""

    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
