from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class PushSubscription(BaseModel):
    """Модель для хранения подписок на push-уведомления."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    endpoint: str
    keys: Dict[str, str]
    expiration_time: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_123",
                "endpoint": "https://fcm.googleapis.com/fcm/send/...",
                "keys": {
                    "p256dh": "base64-encoded-public-key",
                    "auth": "base64-encoded-auth-secret"
                },
                "expiration_time": None,
                "created_at": "2023-08-15T12:30:45.123456",
                "updated_at": None
            }
        } 