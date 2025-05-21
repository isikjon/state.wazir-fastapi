from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from database import Base

class ChatModel(Base):
    __tablename__ = "chats"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Отношения
    user1 = relationship("User", foreign_keys=[user1_id], backref="initiated_chats")
    user2 = relationship("User", foreign_keys=[user2_id], backref="received_chats")
    # Используем обычный backref для messages
    messages = relationship("ChatMessageModel", backref="chat", cascade="all, delete-orphan")
    
    @property
    def last_message(self):
        if not self.messages:
            return None
        return sorted(self.messages, key=lambda m: m.created_at, reverse=True)[0]

class ChatMessageModel(Base):
    __tablename__ = "chat_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Отношения с User через backref
    sender = relationship("User", backref="sent_chat_messages") 