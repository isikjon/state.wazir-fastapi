from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, and_, func

from app.api import deps
from app import models
from schemas.chat import ChatWithLastMessage, ChatCreate, MessageCreate, Message as MessageSchema, Chat
from models.chat import ChatModel, ChatMessageModel

router = APIRouter()

@router.get("/", response_model=List[ChatWithLastMessage])
def get_user_chats(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    chats = db.query(ChatModel).filter(
        or_(
            ChatModel.user1_id == current_user.id,
            ChatModel.user2_id == current_user.id
        )
    ).order_by(ChatModel.updated_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for chat in chats:
        # Определяем другого пользователя в чате
        other_user = chat.user2 if chat.user1_id == current_user.id else chat.user1
        
        # Получаем количество непрочитанных сообщений
        unread_count = db.query(ChatMessageModel).filter(
            ChatMessageModel.chat_id == chat.id,
            ChatMessageModel.sender_id != current_user.id,
            ChatMessageModel.is_read == False
        ).count()
        
        # Получаем последнее сообщение
        last_message = chat.last_message
        
        # Формируем объект для ответа
        chat_data = {
            "id": chat.id,
            "user1_id": chat.user1_id,
            "user2_id": chat.user2_id,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "unread_count": unread_count,
            "other_user_name": f"{other_user.last_name} {other_user.first_name[0]}.",
            "other_user_status": other_user.role.value.capitalize() if hasattr(other_user.role, 'value') else other_user.role.capitalize(),
            "other_user_avatar": other_user.avatar_url if hasattr(other_user, 'avatar_url') else None,
            "is_online": other_user.is_active,
            "last_message": last_message
        }
        
        result.append(ChatWithLastMessage(**chat_data))
    
    return result

@router.get("/{chat_id}", response_model=Chat)
def get_chat(
    chat_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # Проверяем, что текущий пользователь является участником чата
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    return chat

@router.post("/", response_model=Chat)
def create_chat(
    chat_in: ChatCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    # Проверяем, что пользователь создает чат для себя
    if chat_in.user1_id != current_user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    # Проверяем, существует ли уже чат между этими пользователями
    existing_chat = db.query(ChatModel).filter(
        or_(
            and_(ChatModel.user1_id == chat_in.user1_id, ChatModel.user2_id == chat_in.user2_id),
            and_(ChatModel.user1_id == chat_in.user2_id, ChatModel.user2_id == chat_in.user1_id)
        )
    ).first()
    
    if existing_chat:
        return existing_chat
    
    # Создаем новый чат
    chat = ChatModel(**chat_in.model_dump())
    db.add(chat)
    db.commit()
    db.refresh(chat)
    
    return chat

@router.get("/{chat_id}/messages", response_model=List[MessageSchema])
def get_chat_messages(
    chat_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 50
):
    chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # Проверяем, что текущий пользователь является участником чата
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    # Получаем сообщения
    messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.chat_id == chat_id
    ).order_by(ChatMessageModel.created_at.desc()).offset(skip).limit(limit).all()
    
    # Помечаем непрочитанные сообщения как прочитанные
    unread_messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.chat_id == chat_id,
        ChatMessageModel.sender_id != current_user.id,
        ChatMessageModel.is_read == False
    ).all()
    
    for message in unread_messages:
        message.is_read = True
    
    db.commit()
    
    return messages

@router.post("/{chat_id}/messages", response_model=MessageSchema)
def create_message(
    chat_id: int,
    message_in: MessageCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # Проверяем, что текущий пользователь является участником чата
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    # Создаем новое сообщение
    message = ChatMessageModel(
        chat_id=chat_id,
        sender_id=current_user.id,
        content=message_in.content
    )
    
    # Обновляем время последнего обновления чата
    chat.updated_at = func.now()
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message 