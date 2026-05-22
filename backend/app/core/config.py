from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    APP_NAME: str = 'Veteran API'
    APP_VERSION: str = '1.0.0'
    APP_ENV: str = Field(default='development')

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'

    TOKEN_ENCRYPTION_KEY: str
    OPENAI_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str | None = None
    EMBEDDING_PROVIDER: str = 'openai'
    EMBEDDING_MODEL: str = 'text-embedding-3-small'
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_CONTEXT_TOKENS: int = 8192
    EMBEDDING_RESERVED_HEADROOM: int = 1024
    EMBEDDING_COST_PER_1K_USD: float = 0.00002
    ATTACHMENT_STORAGE_PROVIDER: str = 'local'
    ATTACHMENT_STORAGE_PATH: str = '/data/attachments'
    ATTACHMENT_MAX_SIZE_BYTES: int = 26214400
    ATTACHMENT_PARSER_TIMEOUT_SECONDS: int = 10
    ATTACHMENT_PARSER_MAX_CHARS: int = 250000
    WORKER_JOB_TIMEOUT_SECONDS: int = 600
    WORKER_MAX_RETRIES: int = 5
    RETRIEVAL_TOP_K_DEFAULT: int = 10
    RETRIEVAL_TOP_K_MAX: int = 50
    RETRIEVAL_SCORE_THRESHOLD_DEFAULT: float = 0.2
    RETRIEVAL_RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: str = 'http://localhost:3000'

    AUTH_COOKIE_NAME: str = 'veteran_session'

settings = Settings()
