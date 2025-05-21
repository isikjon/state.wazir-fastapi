from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.services.base import CRUDBase
from app.models.message import Message as AppMessage, SupportTicket, TicketResponse
from app.schemas.message import MessageCreate, TicketCreate, TicketUpdate, TicketResponseCreate


class CRUDMessage(CRUDBase[AppMessage, MessageCreate, Any]):
    def create_with_sender(
        self, db: Session, *, obj_in: MessageCreate, sender_id: int
    ) -> AppMessage:
        obj_in_data = obj_in.dict()
        db_obj = AppMessage(**obj_in_data, sender_id=sender_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_user_messages(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AppMessage]:
        return (
            db.query(AppMessage)
            .filter(
                (AppMessage.sender_id == user_id) | (AppMessage.recipient_id == user_id)
            )
            .order_by(AppMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_conversation(
        self, db: Session, *, user_id: int, other_user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AppMessage]:
        return (
            db.query(AppMessage)
            .filter(
                ((AppMessage.sender_id == user_id) & (AppMessage.recipient_id == other_user_id)) |
                ((AppMessage.sender_id == other_user_id) & (AppMessage.recipient_id == user_id))
            )
            .order_by(AppMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class CRUDTicket(CRUDBase[SupportTicket, TicketCreate, TicketUpdate]):
    def create_with_user(
        self, db: Session, *, obj_in: TicketCreate, user_id: int
    ) -> SupportTicket:
        obj_in_data = obj_in.dict()
        db_obj = SupportTicket(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_user_tickets(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[SupportTicket]:
        return (
            db.query(SupportTicket)
            .filter(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class CRUDTicketResponse(CRUDBase[TicketResponse, TicketResponseCreate, Any]):
    def create_response(
        self, db: Session, *, obj_in: TicketResponseCreate, is_from_admin: bool = False
    ) -> TicketResponse:
        obj_in_data = obj_in.dict()
        db_obj = TicketResponse(**obj_in_data, is_from_admin=is_from_admin)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_ticket_responses(
        self, db: Session, *, ticket_id: int, skip: int = 0, limit: int = 100
    ) -> List[TicketResponse]:
        return (
            db.query(TicketResponse)
            .filter(TicketResponse.ticket_id == ticket_id)
            .order_by(TicketResponse.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )


message = CRUDMessage(AppMessage)
ticket = CRUDTicket(SupportTicket)
ticket_response = CRUDTicketResponse(TicketResponse) 