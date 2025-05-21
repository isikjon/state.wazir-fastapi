from fastapi import APIRouter
from api.v1.endpoints import auth, support, chat

api_router = APIRouter()

api_router.include_router(support.router, prefix="/support", tags=["support"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"]) 