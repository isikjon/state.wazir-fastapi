from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class MessageStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="messages_received")


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    RESOLVED = "resolved"


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(255))
    description = Column(Text)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="support_tickets")
    
    responses = relationship("TicketResponse", back_populates="ticket")


class TicketResponse(Base, TimestampMixin):
    __tablename__ = "ticket_responses"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    is_from_admin = Column(Boolean, default=False)
    
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"))
    ticket = relationship("SupportTicket", back_populates="responses") 