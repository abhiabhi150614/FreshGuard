"""Production configuration management"""
import os
from typing import Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/foodspoil"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Device settings
    DEFAULT_DEVICE_URL: str = "http://10.72.89.105"
    POLL_INTERVAL: int = 5
    MAX_HISTORY: int = 2000
    REQUEST_TIMEOUT: float = 3.0
    
    # Thresholds
    RATIO_FRESH: float = 0.8
    RATIO_WARNING: float = 0.5
    
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    WEBHOOK_URL: str = "https://twilio-call-jxu9.onrender.com/voice"
    
    # Monitoring
    PROMETHEUS_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator('TWILIO_ACCOUNT_SID')
    def validate_twilio_sid(cls, v):
        if v and not v.startswith('AC'):
            raise ValueError('Invalid Twilio Account SID')
        return v

settings = Settings()