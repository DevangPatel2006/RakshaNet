import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: str = "dev"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:55432/rakshanet"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4jpassword"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    JWT_SECRET: str = "supersecretkeyforrakshanetdev"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    CORS_ORIGINS: str = "http://localhost:5173"

settings = Settings()
