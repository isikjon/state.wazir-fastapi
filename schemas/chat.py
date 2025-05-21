from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    chat_id: int
    sender_id: int

class Message(MessageBase):
    id: int
    chat_id: int
    sender_id: int
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    user1_id: int
    user2_id: int

class ChatCreate(ChatBase):
    pass

class Chat(ChatBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatWithLastMessage(Chat):
    last_message: Optional[Message] = None
    unread_count: int = 0
    other_user_name: str
    other_user_status: str
    other_user_avatar: Optional[str] = None
    is_online: bool = False 