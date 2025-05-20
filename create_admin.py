from sqlalchemy.orm import Session
from app.models.user import User, UserRole, UserStatus
from app.utils.security import get_password_hash
from database import SessionLocal

def create_admin_user():
    db = SessionLocal()
    try:
        # Проверяем, существует ли уже админ с таким email
        admin_user = db.query(User).filter(User.email == "admin@wazir.ru").first()
        
        if admin_user:
            print(f"Администратор admin@wazir.ru уже существует!")
            return
        
        # Создаем нового пользователя-админа
        new_admin = User(
            email="admin@wazir.ru",
            phone="admin",  # Использую 'admin' как логин в поле телефона
            hashed_password=get_password_hash("123"),  # Хешируем пароль
            full_name="Администратор",
            is_active=True,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print(f"Администратор успешно создан!")
        print(f"Логин: admin или admin@wazir.ru")
        print(f"Пароль: 123")
        
    except Exception as e:
        print(f"Ошибка при создании администратора: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user() 