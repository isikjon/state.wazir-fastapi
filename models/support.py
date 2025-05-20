from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta

from db.base_class import Base

class SupportTicket(Base):
    """Модель тикета техподдержки"""
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="new")  # new, active, waiting, closed
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Отношения
    user = relationship("User", back_populates="support_tickets")
    messages = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan")
    
    @property
    def status_class(self):
        """Возвращает CSS-класс для статуса тикета"""
        status_classes = {
            "new": "status-new",
            "active": "status-active",
            "waiting": "status-waiting",
            "closed": "status-closed"
        }
        return status_classes.get(self.status, "")
    
    @property
    def status_display(self):
        """Возвращает текстовое представление статуса тикета на русском"""
        status_names = {
            "new": "Новый",
            "active": "Активный",
            "waiting": "Ожидает",
            "closed": "Закрыт"
        }
        return status_names.get(self.status, "")
    
    @property
    def last_message(self):
        """Возвращает последнее сообщение в тикете"""
        if not self.messages:
            return None
        return sorted(self.messages, key=lambda m: m.created_at, reverse=True)[0]
    
    @property
    def last_message_preview(self):
        """Возвращает превью последнего сообщения (первые 50 символов)"""
        message = self.last_message
        if not message:
            return ""
        
        preview = message.content
        if len(preview) > 50:
            preview = preview[:50] + "..."
        
        return preview
    
    @property
    def last_message_time(self):
        """Возвращает время последнего сообщения в удобном формате"""
        message = self.last_message
        if not message:
            return ""
        
        now = func.now()
        created_at = message.created_at
        
        if created_at.date() == now.date():
            # Сегодня: HH:MM
            return created_at.strftime("%H:%M")
        elif created_at.date() == (now - timedelta(days=1)).date():
            # Вчера
            return "Вчера"
        else:
            # Другие даты: DD.MM
            return created_at.strftime("%d.%m")

class SupportMessage(Base):
    """Модель сообщения в тикете техподдержки"""
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_admin = Column(Boolean, default=False)
    admin_id = Column(Integer, nullable=True)  # ID администратора, если сообщение от админа
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Отношения
    ticket = relationship("SupportTicket", back_populates="messages")
    
    @property
    def time(self):
        """Возвращает время создания сообщения в формате HH:MM"""
        return self.created_at.strftime("%H:%M") 