from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

# Схемы для сообщений
class SupportMessageBase(BaseModel):
    content: str

class SupportMessageCreate(SupportMessageBase):
    ticket_id: int

class SupportMessageResponse(SupportMessageBase):
    id: int
    ticket_id: int
    chat_id: Optional[int] = None  # ID связанного чата
    is_admin: bool
    admin_id: Optional[int] = None
    user_id: Optional[int] = None  # ID пользователя, если не админ
    is_read: bool
    time: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Схемы для тикетов
class SupportTicketBase(BaseModel):
    subject: str
    description: Optional[str] = None

class SupportTicketCreate(SupportTicketBase):
    message: Optional[str] = None  # Опциональное первое сообщение при создании тикета
    chat_id: Optional[int] = None  # Опциональный ID связанного чата

class SupportTicketUpdate(BaseModel):
    status: Optional[str] = None
    chat_id: Optional[int] = None

class SupportTicketResponse(SupportTicketBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    chat_id: Optional[int] = None  # ID связанного чата
    
    class Config:
        from_attributes = True

# Расширенная схема для тикета с сообщениями
class SupportTicketWithMessages(SupportTicketResponse):
    messages: List[SupportMessageResponse] = []
    
    class Config:
        from_attributes = True 