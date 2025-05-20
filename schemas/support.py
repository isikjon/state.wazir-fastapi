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
    is_admin: bool
    admin_id: Optional[int] = None
    is_read: bool
    time: str
    created_at: datetime
    
    class Config:
        orm_mode = True

# Схемы для тикетов
class SupportTicketBase(BaseModel):
    subject: str

class SupportTicketCreate(SupportTicketBase):
    message: Optional[str] = None  # Опциональное первое сообщение при создании тикета

class SupportTicketUpdate(BaseModel):
    status: Optional[str] = None

class SupportTicketResponse(SupportTicketBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Расширенная схема для тикета с сообщениями
class SupportTicketWithMessages(SupportTicketResponse):
    messages: List[SupportMessageResponse] = []
    
    class Config:
        orm_mode = True 