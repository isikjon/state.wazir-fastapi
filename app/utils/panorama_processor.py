import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pathlib import Path
from PIL import Image
from fastapi import UploadFile, HTTPException
import io

from .media_uploader import media_uploader

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PanoramaProcessor:
    
    MAX_FILE_SIZE = 100 * 1024 * 1024
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
    
    def __init__(self):
        logger.info("🚀 Инициализация PanoramaProcessor")
        logger.info("✅ PanoramaProcessor настроен для работы с медиа сервером")
    
    def validate_file(self, file_input: Union[bytes, Path, str], file_size: int) -> bool:
        logger.info("🔍 Валидация файла панорамы")
        
        if file_size > self.MAX_FILE_SIZE:
            logger.error(f"❌ Файл слишком большой: {file_size} байт")
            return False
        
        try:
            if isinstance(file_input, (Path, str)):
                with open(file_input, 'rb') as f:
                    file_data = f.read()
                image = Image.open(io.BytesIO(file_data))
            else:
                image = Image.open(io.BytesIO(file_input))
            
            width, height = image.size
            logger.info(f"📐 Размеры изображения: {width}x{height}")
            
            if width < 2048 or height < 1024:
                logger.error(f"❌ Неподходящие размеры для панорамы: {width}x{height}")
                return False
            
            aspect_ratio = width / height
            if not (1.8 <= aspect_ratio <= 2.2):
                logger.warning(f"⚠️ Необычное соотношение сторон: {aspect_ratio:.2f}")
            
            logger.info("✅ Файл панорамы валиден")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации изображения: {str(e)}")
            return False
    
    async def upload_panorama(self, file: UploadFile, service_card_id: int) -> Dict[str, Any]:
        try:
            logger.info(f"🚀 Начинаем загрузку панорамы для service_card_id: {service_card_id}")
            
            file_content = await file.read()
            file_size = len(file_content)
            
            if not self.validate_file(file_content, file_size):
                raise HTTPException(status_code=400, detail="Файл не является валидным изображением")
            
            property_id = f"service_card_{service_card_id}"
            
            file_data = {
                'content': file_content,
                'filename': file.filename
            }
            
            result = await media_uploader.upload_panorama(file_data, property_id)
            
            if result.get("status") == "success":
                logger.info("✅ Панорама успешно загружена")
                return {
                    "success": True,
                    "file_id": result.get("file_id"),
                    "urls": {
                        "original": result.get("original_url"),
                        "optimized": result.get("optimized_url"),
                        "preview": result.get("preview_url"),
                        "thumbnail": result.get("thumbnail_url")
                    },
                    "meta": result.get("metadata", {})
                }
            else:
                logger.error(f"❌ Ошибка загрузки: {result.get('message')}")
                raise HTTPException(status_code=500, detail=result.get("message", "Upload failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при загрузке 360° панорамы: {str(e)}")
        finally:
            await file.seek(0)

panorama_processor = PanoramaProcessor() 