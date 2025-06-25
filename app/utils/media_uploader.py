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
            print(f"DEBUG: Подготовка к загрузке {len(files)} файлов для property_id: {property_id}")
            
            # Подготавливаем файлы для отправки - ИСПРАВЛЕННЫЙ СПОСОБ
            # Отправляем все файлы с именем "images[]" чтобы PHP правильно их обработал
            files_data = []
            for i, file in enumerate(files):
                file_content = await file.read()
                file_size = len(file_content)
                print(f"DEBUG: Файл {i+1}: {file.filename}, размер: {file_size} байт, тип: {file.content_type}")
                
                # Используем "images[]" как в вашем PHP коде
                files_data.append(
                    ("images[]", (file.filename, file_content, file.content_type))
                )
                # Сбрасываем указатель файла
                await file.seek(0)
            
            print(f"DEBUG: Всего подготовлено {len(files_data)} файлов для отправки с именем 'images[]'")
            
            # Отправляем на медиа-сервер
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"DEBUG: Отправляем POST запрос на {self.base_url}/upload.php")
                response = await client.post(
                    f"{self.base_url}/upload.php",
                    files=files_data,
                    data={"property_id": property_id}
                )
                
                print(f"DEBUG: Получен ответ со статусом: {response.status_code}")
                print(f"DEBUG: Тело ответа: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"DEBUG: Результат парсинга JSON: {result}")
                    
                    # Обновляем структуру в соответствии с новым форматом ответа PHP
                    updated_files = []
                    for file_info in result.get("files", []):
                        # PHP возвращает структуру: {'file_id': '...', 'original_name': '...', 'urls': {...}}
                        file_id = file_info.get('file_id')
                        original_name = file_info.get('original_name')
                        urls = file_info.get('urls', {})
                        
                        # Формируем единый объект с нужными данными
                        updated_file_info = {
                            'file_id': file_id,
                            'filename': f"{file_id}.jpg",  # Генерируем имя файла
                            'original_name': original_name,
                            'urls': urls,
                            # Для обратной совместимости добавляем основной URL
                            'url': urls.get('large') or urls.get('medium') or urls.get('original', '')
                        }
                        updated_files.append(updated_file_info)
                    
                    return {
                        "status": "success",
                        "property_id": property_id,
                        "files": updated_files,
                        "count": result.get("count", 0),
                        "message": result.get("message", "Upload successful"),
                        "debug": result.get("debug", {})
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Upload failed with status {response.status_code}",
                        "response": response.text
                    }
                    
        except Exception as e:
            print(f"ERROR: Ошибка при загрузке изображений: {str(e)}")
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
    
    async def upload_file(self, file: UploadFile, folder: str = "service_cards") -> Dict[str, Any]:
        """Загружает один файл (для совместимости со старым кодом)"""
        try:
            file_content = await file.read()
            file_id = str(uuid.uuid4())
            
            # Определяем расширение файла
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            filename = f"{file_id}.{file_extension}"
            
            # Отправляем файл
            async with httpx.AsyncClient(timeout=30.0) as client:
                files_data = [("file", (filename, file_content, file.content_type))]
                response = await client.post(
                    f"{self.base_url}/upload_single.php",
                    files=files_data,
                    data={"folder": folder}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "file_id": file_id,
                        "filename": filename,
                        "url": result.get("url", f"/media/{folder}/{filename}"),
                        "message": "File uploaded successfully"
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

# Создаем экземпляр
media_uploader = MediaUploader() 