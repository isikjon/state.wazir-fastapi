import httpx
import uuid
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
import asyncio

class MediaUploader:
    def __init__(self, media_server_url: str = "https://wazir.kg/state"):
        self.base_url = media_server_url
        
    def generate_property_id(self) -> str:
        """Генерирует ID в формате xxxx-xxxx-xxxx-xxxx"""
        hex_chars = f"{uuid.uuid4().hex}"
        return f"{hex_chars[0:4]}-{hex_chars[4:8]}-{hex_chars[8:12]}-{hex_chars[12:16]}"
    
    async def ping_server(self) -> Dict[str, Any]:
        """Проверка связи с медиа-сервером"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/upload.php?ping=1")
                if response.status_code == 200:
                    return {
                        "status": "success",
                        "data": response.json(),
                        "connected": True
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Server returned {response.status_code}",
                        "connected": False
                    }
        except Exception as e:
            return {
                "status": "error", 
                "message": str(e),
                "connected": False
            }
    
    async def upload_property_images(
        self, 
        files: List[UploadFile], 
        property_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Загружает изображения для объявления"""
        
        if not property_id:
            property_id = self.generate_property_id()
        
        if not files:
            return {
                "status": "error",
                "message": "No files provided"
            }
        
        try:
            # Подготавливаем файлы для отправки
            files_data = []
            for file in files:
                file_content = await file.read()
                files_data.append(
                    ("images", (file.filename, file_content, file.content_type))
                )
                # Сбрасываем указатель файла
                await file.seek(0)
            
            # Отправляем на медиа-сервер
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/upload.php",
                    files=files_data,
                    data={"property_id": property_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "property_id": property_id,
                        "files": result.get("files", []),
                        "count": result.get("count", 0)
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Upload failed with status {response.status_code}",
                        "response": response.text
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"Upload error: {str(e)}"
            }
    
    async def delete_property_images(self, property_id: str) -> Dict[str, Any]:
        """Удаляет все изображения объявления"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/delete.php",
                    data={"property_id": property_id}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "status": "error", 
                        "message": f"Delete failed with status {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Delete error: {str(e)}"
            }

# Создаем экземпляр
media_uploader = MediaUploader() 