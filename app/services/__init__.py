from .user import user
from .property import property, CRUDCategory
from .message import message, ticket
from .request import request
from app.models.property import Category

# Создаем экземпляр CRUDCategory и экспортируем его
category = CRUDCategory(Category) 