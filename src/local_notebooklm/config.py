from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    discord_token: str = Field(alias="DISCORD_TOKEN")
    lmstudio_base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="LMSTUDIO_BASE_URL")
    lmstudio_model: str = Field(default="local-model", alias="LMSTUDIO_MODEL")
    lmstudio_timeout_seconds: int = Field(default=300, alias="LMSTUDIO_TIMEOUT_SECONDS")

    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )
    chunk_size: int = Field(default=1200, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    top_k: int = Field(default=6, alias="TOP_K")
    max_context_chunks: int = Field(default=8, alias="MAX_CONTEXT_CHUNKS")


settings = Settings()
