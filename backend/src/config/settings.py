"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # PostgreSQL 16
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "crawlfq_db"
    db_user: str = "crawlfq_user"
    db_password: str = "crawlfq_pwd_2026"

    # 安全
    jwt_secret: str = "crawlfq_dev_jwt_secret_change_me_20261110"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    seed_demo: bool = True
    rate_limit_write_per_minute: int = 240
    artifact_dir: str = "/data/artifacts"

    # 算法 A：布隆过滤器
    bloom_bits: int = 1 << 20
    bloom_k: int = 5

    # 算法 B：调度模拟（虚拟时钟）
    sim_window_s: float = 20.0
    sim_max_sequence: int = 40
    sim_seed: int = 7

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
