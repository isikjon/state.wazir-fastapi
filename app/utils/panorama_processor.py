import os
import uuid
import cv2
import numpy as np
from PIL import Image, ExifTags
from typing import Optional, Tuple, Dict, Any
import aiofiles
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)

class PanoramaProcessor:
    """Класс для обработки 360° панорам"""
    
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    PREVIEW_WIDTH = 800
    PREVIEW_HEIGHT = 400
    THUMBNAIL_WIDTH = 200
    THUMBNAIL_HEIGHT = 100
    
    def __init__(self, upload_dir: str = "static/uploads/360"):
        self.upload_dir = upload_dir
        self.ensure_upload_dir()
    
    def ensure_upload_dir(self):
        """Создает директории для загрузки файлов"""
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(f"{self.upload_dir}/originals", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/previews", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/thumbnails", exist_ok=True)
    
    def validate_panorama_file(self, file: UploadFile) -> bool:
        """Валидирует файл 360° панорамы"""
        # Проверка расширения файла
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Проверка размера файла
        if hasattr(file, 'size') and file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Файл слишком большой. Максимальный размер: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        return True
    
    def check_panorama_format(self, image_array: np.ndarray) -> Dict[str, Any]:
        """Проверяет, является ли изображение 360° панорамой"""
        height, width = image_array.shape[:2]
        aspect_ratio = width / height
        
        # Стандартные соотношения для 360° панорам
        is_equirectangular = 1.8 <= aspect_ratio <= 2.2  # Обычно 2:1
        is_panorama = aspect_ratio >= 1.5  # Широкие панорамы
        
        confidence = 0.0
        format_type = "unknown"
        
        if is_equirectangular:
            confidence = 0.9
            format_type = "equirectangular"
        elif is_panorama:
            confidence = 0.6
            format_type = "wide_panorama"
        
        return {
            "is_panorama": is_panorama or is_equirectangular,
            "format_type": format_type,
            "confidence": confidence,
            "aspect_ratio": aspect_ratio,
            "dimensions": {"width": width, "height": height}
        }
    
    def extract_metadata(self, image_path: str) -> Dict[str, Any]:
        """Извлекает метаданные из изображения"""
        try:
            with Image.open(image_path) as img:
                metadata = {}
                
                # EXIF данные
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        metadata[tag] = value
                
                # Основные свойства
                metadata.update({
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                })
                
                return metadata
        except Exception as e:
            logger.warning(f"Не удалось извлечь метаданные: {e}")
            return {}
    
    def create_preview(self, input_path: str, output_path: str) -> bool:
        """Создает превью изображения для быстрой загрузки"""
        try:
            with Image.open(input_path) as img:
                # Пропорциональное изменение размера
                img.thumbnail((self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT), Image.Resampling.LANCZOS)
                
                # Сохраняем с оптимизацией
                img.save(output_path, "JPEG", quality=85, optimize=True, progressive=True)
                return True
        except Exception as e:
            logger.error(f"Ошибка создания превью: {e}")
            return False
    
    def create_thumbnail(self, input_path: str, output_path: str) -> bool:
        """Создает миниатюру изображения"""
        try:
            with Image.open(input_path) as img:
                img.thumbnail((self.THUMBNAIL_WIDTH, self.THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
                img.save(output_path, "JPEG", quality=80, optimize=True)
                return True
        except Exception as e:
            logger.error(f"Ошибка создания миниатюры: {e}")
            return False
    
    def optimize_panorama(self, input_path: str, output_path: str) -> bool:
        """Оптимизирует панораму для веб-отображения"""
        try:
            # Читаем изображение
            img = cv2.imread(input_path)
            if img is None:
                return False
            
            height, width = img.shape[:2]
            
            # Ограничиваем максимальный размер для веб-отображения
            max_width = 4096
            if width > max_width:
                scale = max_width / width
                new_width = max_width
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # Улучшаем качество
            img = cv2.bilateralFilter(img, 9, 75, 75)
            
            # Сохраняем с оптимизацией
            cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return True
            
        except Exception as e:
            logger.error(f"Ошибка оптимизации панорамы: {e}")
            return False
    
    async def process_panorama(self, file: UploadFile, property_id: int) -> Dict[str, Any]:
        """Основной метод обработки 360° панорамы"""
        try:
            # Валидация файла
            self.validate_panorama_file(file)
            
            # Генерируем уникальные имена файлов
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(file.filename.lower())[1]
            
            original_filename = f"{property_id}_{file_id}_original{file_ext}"
            preview_filename = f"{property_id}_{file_id}_preview.jpg"
            thumbnail_filename = f"{property_id}_{file_id}_thumb.jpg"
            optimized_filename = f"{property_id}_{file_id}_optimized.jpg"
            
            # Пути к файлам
            original_path = os.path.join(self.upload_dir, "originals", original_filename)
            preview_path = os.path.join(self.upload_dir, "previews", preview_filename)
            thumbnail_path = os.path.join(self.upload_dir, "thumbnails", thumbnail_filename)
            optimized_path = os.path.join(self.upload_dir, "originals", optimized_filename)
            
            # Сохраняем оригинальный файл
            async with aiofiles.open(original_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Проверяем, является ли изображение панорамой
            img_array = cv2.imread(original_path)
            panorama_info = self.check_panorama_format(img_array)
            
            if not panorama_info["is_panorama"]:
                # Удаляем файл, если это не панорама
                os.remove(original_path)
                raise HTTPException(
                    status_code=400,
                    detail="Загруженное изображение не является 360° панорамой. Соотношение сторон должно быть примерно 2:1"
                )
            
            # Извлекаем метаданные
            metadata = self.extract_metadata(original_path)
            
            # Создаем превью и миниатюру
            preview_created = self.create_preview(original_path, preview_path)
            thumbnail_created = self.create_thumbnail(original_path, thumbnail_path)
            
            # Оптимизируем панораму
            optimized_created = self.optimize_panorama(original_path, optimized_path)
            
            # Формируем URL для доступа к файлам
            base_url = "/static/uploads/360"
            
            result = {
                "success": True,
                "file_id": file_id,
                "original_filename": original_filename,
                "urls": {
                    "original": f"{base_url}/originals/{original_filename}",
                    "optimized": f"{base_url}/originals/{optimized_filename}" if optimized_created else f"{base_url}/originals/{original_filename}",
                    "preview": f"{base_url}/previews/{preview_filename}" if preview_created else None,
                    "thumbnail": f"{base_url}/thumbnails/{thumbnail_filename}" if thumbnail_created else None,
                },
                "panorama_info": panorama_info,
                "metadata": metadata,
                "file_size": len(content),
                "processing_status": {
                    "preview_created": preview_created,
                    "thumbnail_created": thumbnail_created,
                    "optimized_created": optimized_created
                }
            }
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка обработки панорамы: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    def delete_panorama_files(self, file_id: str, property_id: int) -> bool:
        """Удаляет все файлы панорамы"""
        try:
            patterns = [
                f"{property_id}_{file_id}_original.*",
                f"{property_id}_{file_id}_preview.jpg",
                f"{property_id}_{file_id}_thumb.jpg",
                f"{property_id}_{file_id}_optimized.jpg"
            ]
            
            import glob
            deleted_count = 0
            
            for pattern in patterns:
                for subdir in ["originals", "previews", "thumbnails"]:
                    files = glob.glob(os.path.join(self.upload_dir, subdir, pattern))
                    for file_path in files:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except OSError:
                            pass
            
            return deleted_count > 0
        except Exception as e:
            logger.error(f"Ошибка удаления файлов панорамы: {e}")
            return False


# Глобальный экземпляр процессора
panorama_processor = PanoramaProcessor() 