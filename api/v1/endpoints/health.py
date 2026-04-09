from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api import deps
from datetime import datetime

router = APIRouter()

@router.get("/", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(deps.get_db)):
    """
    Проверка работоспособности API и подключения к базе данных
    """
    try:
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "message": "API работает нормально, соединение с базой данных установлено"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ошибка проверки работоспособности: {str(e)}"
        )
