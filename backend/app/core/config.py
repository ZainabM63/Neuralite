from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    PRIMARY_MODEL: str = "llama-3.3-70b-versatile"
    SECONDARY_MODEL: str = "llama3-groq-70b-tool-use"
    RAG_PERSIST_DIR: str = "./chroma_db"
    
    class Config:
        env_file = ".env"
        extra = "allow"

 
settings = Settings()
print(settings.GROQ_API_KEY)
