import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Adjusted chunk settings for large PDFs
    CHUNK_SIZE: int = 1500  # Increased from 1000
    CHUNK_OVERLAP: int = 300  # Increased from 200
    
    # ChromaDB settings
    MAX_BATCH_SIZE: int = 5000
    
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    class Config:
        env_file = ".env"

settings = Settings()