from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.api import deps

router = APIRouter()


@router.get("/tickets", response_model=List[schemas.Ticket])
def read_tickets(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    if services.user.is_admin(current_user):
        tickets = services.ticket.get_multi(db=db, skip=skip, limit=limit)
    else:
        tickets = services.ticket.get_user_tickets(
            db=db, user_id=current_user.id, skip=skip, limit=limit
        )
    return tickets


@router.post("/tickets", response_model=schemas.Ticket)
def create_ticket(
    *,
    db: Session = Depends(deps.get_db),
    ticket_in: schemas.TicketCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.create_with_user(
        db=db, obj_in=ticket_in, user_id=current_user.id
    )
    return ticket


@router.get("/tickets/{ticket_id}", response_model=schemas.Ticket)
def read_ticket(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    if ticket.user_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этого тикета",
        )
    
    return ticket


@router.put("/tickets/{ticket_id}", response_model=schemas.Ticket)
def update_ticket(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    ticket_in: schemas.TicketUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    if not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут обновлять статус тикетов",
        )
    
    ticket = services.ticket.update(db=db, db_obj=ticket, obj_in=ticket_in)
    return ticket


@router.post("/tickets/{ticket_id}/responses", response_model=schemas.TicketResponse)
def create_ticket_response(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    response_in: schemas.TicketResponseCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    is_from_admin = services.user.is_admin(current_user)
    
    if ticket.user_id != current_user.id and not is_from_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не можете отвечать на этот тикет",
        )
    
    response = services.ticket_response.create_response(
        db=db, obj_in=response_in, is_from_admin=is_from_admin
    )
    return response


@router.get("/tickets/{ticket_id}/responses", response_model=List[schemas.TicketResponse])
def read_ticket_responses(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    if ticket.user_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра ответов на этот тикет",
        )
    
    responses = services.ticket_response.get_ticket_responses(
        db=db, ticket_id=ticket_id, skip=skip, limit=limit
    )
    return responses 