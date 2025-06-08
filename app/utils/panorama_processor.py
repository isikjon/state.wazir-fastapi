import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageOps
import cv2
import numpy as np
import aiofiles
from fastapi import UploadFile, HTTPException

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PanoramaProcessor:
    """Класс для обработки и оптимизации 360° панорам"""
    
    # Увеличиваем максимальный размер файла до 100MB
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB в байтах
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
    
    # Директории для сохранения файлов
    UPLOAD_DIR = Path("uploads") / "panoramas"
    ORIGINAL_DIR = UPLOAD_DIR / "original"
    OPTIMIZED_DIR = UPLOAD_DIR / "optimized"
    PREVIEW_DIR = UPLOAD_DIR / "preview"
    THUMBNAIL_DIR = UPLOAD_DIR / "thumbnails"
    
    def __init__(self):
        """Инициализация процессора"""
        logger.info("🚀 Инициализация PanoramaProcessor")
        self._create_directories()
        logger.info("✅ PanoramaProcessor успешно инициализирован")
    
    def _create_directories(self):
        """Создание необходимых директорий"""
        logger.debug("📁 Создание директорий для панорам...")
        directories = [
            self.ORIGINAL_DIR,
            self.OPTIMIZED_DIR, 
            self.PREVIEW_DIR,
            self.THUMBNAIL_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"✅ Директория создана: {directory}")
        
        logger.info("✅ Все директории созданы успешно")
    
    def validate_file(self, file_path: Path, file_size: int = None) -> bool:
        """Валидация файла панорамы"""
        logger.info(f"🔍 Начинаем валидацию файла: {file_path}")
        
        # Проверка существования файла
        if not file_path.exists():
            logger.error(f"❌ Файл не существует: {file_path}")
            return False
        
        logger.debug(f"✅ Файл существует: {file_path}")
        
        # Проверка размера файла
        actual_size = file_path.stat().st_size if file_size is None else file_size
        logger.debug(f"📏 Размер файла: {actual_size} байт ({actual_size / (1024*1024):.2f} MB)")
        
        if actual_size > self.MAX_FILE_SIZE:
            logger.error(f"❌ Файл слишком большой: {actual_size} > {self.MAX_FILE_SIZE}")
            return False
        
        logger.debug("✅ Размер файла допустимый")
        
        # Проверка расширения файла
        file_extension = file_path.suffix.lower()
        logger.debug(f"📄 Расширение файла: {file_extension}")
        
        if file_extension not in self.SUPPORTED_FORMATS:
            logger.error(f"❌ Неподдерживаемый формат файла: {file_extension}")
            return False
        
        logger.debug("✅ Формат файла поддерживается")
        
        # Проверка является ли файл изображением
        try:
            logger.debug("🖼️ Проверка файла как изображения...")
            with Image.open(file_path) as img:
                width, height = img.size
                logger.debug(f"📐 Размеры изображения: {width}x{height}")
                
                # Проверка соотношения сторон (должно быть примерно 2:1 для панорамы)
                aspect_ratio = width / height
                logger.debug(f"�� Соотношение сторон: {aspect_ratio:.2f}")
                
                if not (1.8 <= aspect_ratio <= 2.2):
                    logger.warning(f"⚠️ Подозрительное соотношение сторон: {aspect_ratio:.2f} (ожидается ~2:1)")
                    # Не блокируем, только предупреждаем
                
                logger.info("✅ Файл прошел валидацию успешно")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка при открытии изображения: {str(e)}")
            return False
    
    def process_panorama(self, input_file: Path, property_id: int) -> Dict[str, Any]:
        """Полная обработка панорамы"""
        logger.info(f"🎯 Начинаем обработку панорамы для свойства ID: {property_id}")
        logger.info(f"📂 Входной файл: {input_file}")
        
        try:
            # Генерация уникального ID для файлов
            file_id = str(uuid.uuid4())
            logger.debug(f"🆔 Сгенерирован file_id: {file_id}")
            
            # Определение расширения файла
            file_extension = input_file.suffix.lower()
            base_filename = f"{property_id}_{file_id}"
            logger.debug(f"📋 Базовое имя файла: {base_filename}")
            
            # Пути для сохранения различных версий
            original_path = self.ORIGINAL_DIR / f"{base_filename}_original{file_extension}"
            optimized_path = self.OPTIMIZED_DIR / f"{base_filename}_optimized.jpg"
            preview_path = self.PREVIEW_DIR / f"{base_filename}_preview.jpg"
            thumbnail_path = self.THUMBNAIL_DIR / f"{base_filename}_thumbnail.jpg"
            
            logger.debug(f"📍 Пути файлов:")
            logger.debug(f"  Original: {original_path}")
            logger.debug(f"  Optimized: {optimized_path}")
            logger.debug(f"  Preview: {preview_path}")
            logger.debug(f"  Thumbnail: {thumbnail_path}")
            
            # Копирование оригинального файла
            logger.info("📥 Сохранение оригинального файла...")
            import shutil
            shutil.copy2(input_file, original_path)
            logger.info(f"✅ Оригинальный файл сохранен: {original_path}")
            
            # Загрузка изображения для обработки
            logger.info("🖼️ Загрузка изображения для обработки...")
            with Image.open(input_file) as img:
                original_size = img.size
                logger.debug(f"📐 Оригинальный размер: {original_size}")
                
                # Извлечение метаданных
                logger.info("📊 Извлечение метаданных...")
                metadata = self._extract_metadata(img, input_file)
                logger.debug(f"📄 Метаданные: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
                
                # Создание оптимизированной версии
                logger.info("⚡ Создание оптимизированной версии...")
                self._create_optimized_version(img, optimized_path)
                logger.info(f"✅ Оптимизированная версия создана: {optimized_path}")
                
                # Создание превью
                logger.info("🔍 Создание превью...")
                self._create_preview_version(img, preview_path)
                logger.info(f"✅ Превью создано: {preview_path}")
                
                # Создание миниатюры
                logger.info("🖼️ Создание миниатюры...")
                self._create_thumbnail_version(img, thumbnail_path)
                logger.info(f"✅ Миниатюра создана: {thumbnail_path}")
            
            # Формирование результата
            result = {
                'file_id': file_id,
                'original_url': f"/uploads/panoramas/original/{original_path.name}",
                'optimized_url': f"/uploads/panoramas/optimized/{optimized_path.name}",
                'preview_url': f"/uploads/panoramas/preview/{preview_path.name}",
                'thumbnail_url': f"/uploads/panoramas/thumbnails/{thumbnail_path.name}",
                'metadata': metadata,
                'uploaded_at': datetime.now()
            }
            
            logger.info("🎉 Обработка панорамы завершена успешно!")
            logger.debug(f"📋 Результат: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка при обработке панорамы: {str(e)}")
            logger.exception("Полный стек ошибки:")
            raise Exception(f"Ошибка обработки панорамы: {str(e)}")
    
    def _extract_metadata(self, img: Image.Image, file_path: Path) -> Dict[str, Any]:
        """Извлечение метаданных изображения"""
        logger.debug("📊 Извлечение метаданных изображения...")
        
        try:
            file_stats = file_path.stat()
            
            metadata = {
                'width': img.size[0],
                'height': img.size[1], 
                'format': img.format,
                'mode': img.mode,
                'file_size': file_stats.st_size,
                'aspect_ratio': round(img.size[0] / img.size[1], 2),
                'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            }
            
            # Попытка извлечь EXIF данные
            if hasattr(img, '_getexif') and img._getexif():
                exif_data = img._getexif()
                logger.debug(f"📷 Найдены EXIF данные: {len(exif_data)} записей")
                metadata['exif_available'] = True
            else:
                logger.debug("📷 EXIF данные не найдены")
                metadata['exif_available'] = False
            
            logger.debug("✅ Метаданные успешно извлечены")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения метаданных: {str(e)}")
            return {'error': str(e)}
    
    def _create_optimized_version(self, img: Image.Image, output_path: Path):
        """Создание оптимизированной версии панорамы"""
        logger.debug("⚡ Создание оптимизированной версии...")
        
        try:
            # Максимальная ширина для оптимизированной версии
            max_width = 4096
            
            if img.size[0] > max_width:
                logger.debug(f"📏 Уменьшение размера с {img.size[0]} до {max_width} пикселей по ширине")
                ratio = max_width / img.size[0]
                new_height = int(img.size[1] * ratio)
                img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"✅ Размер изменен на: {img_resized.size}")
            else:
                logger.debug("📏 Размер не требует изменения")
                img_resized = img
            
            # Конвертация в RGB если необходимо
            if img_resized.mode != 'RGB':
                logger.debug(f"🎨 Конвертация из {img_resized.mode} в RGB")
                img_resized = img_resized.convert('RGB')
            
            # Сохранение с оптимизацией
            logger.debug("💾 Сохранение оптимизированной версии...")
            img_resized.save(
                output_path,
                'JPEG',
                quality=85,
                optimize=True,
                progressive=True
            )
            
            logger.debug("✅ Оптимизированная версия сохранена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания оптимизированной версии: {str(e)}")
            raise
    
    def _create_preview_version(self, img: Image.Image, output_path: Path):
        """Создание превью версии"""
        logger.debug("🔍 Создание превью версии...")
        
        try:
            # Размер превью
            preview_width = 1024
            ratio = preview_width / img.size[0]
            preview_height = int(img.size[1] * ratio)
            
            logger.debug(f"📏 Размер превью: {preview_width}x{preview_height}")
            
            img_preview = img.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
            
            if img_preview.mode != 'RGB':
                img_preview = img_preview.convert('RGB')
            
            img_preview.save(
                output_path,
                'JPEG',
                quality=75,
                optimize=True
            )
            
            logger.debug("✅ Превью версия сохранена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания превью: {str(e)}")
            raise
    
    def _create_thumbnail_version(self, img: Image.Image, output_path: Path):
        """Создание миниатюры"""
        logger.debug("🖼️ Создание миниатюры...")
        
        try:
            # Размер миниатюры
            thumbnail_size = (400, 200)
            
            logger.debug(f"📏 Размер миниатюры: {thumbnail_size}")
            
            img_thumbnail = img.resize(thumbnail_size, Image.Resampling.LANCZOS)
            
            if img_thumbnail.mode != 'RGB':
                img_thumbnail = img_thumbnail.convert('RGB')
            
            img_thumbnail.save(
                output_path,
                'JPEG',
                quality=70,
                optimize=True
            )
            
            logger.debug("✅ Миниатюра сохранена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания миниатюры: {str(e)}")
            raise
    
    def delete_panorama_files(self, file_id: str, property_id: int):
        """Удаление всех файлов панорамы"""
        logger.info(f"🗑️ Удаление файлов панорамы: file_id={file_id}, property_id={property_id}")
        
        try:
            base_filename = f"{property_id}_{file_id}"
            files_to_delete = []
            
            # Поиск всех файлов с данным file_id
            for directory in [self.ORIGINAL_DIR, self.OPTIMIZED_DIR, self.PREVIEW_DIR, self.THUMBNAIL_DIR]:
                for file_path in directory.glob(f"{base_filename}*"):
                    files_to_delete.append(file_path)
            
            logger.debug(f"📋 Найдено файлов для удаления: {len(files_to_delete)}")
            
            # Удаление файлов
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    if file_path.exists():
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"✅ Удален файл: {file_path}")
                    else:
                        logger.debug(f"⚠️ Файл уже не существует: {file_path}")
                except Exception as e:
                    logger.error(f"❌ Ошибка удаления файла {file_path}: {str(e)}")
            
            logger.info(f"🎯 Удаление завершено: {deleted_count} файлов удалено")
            
        except Exception as e:
            logger.error(f"💥 Ошибка при удалении файлов панорамы: {str(e)}")
            raise


# Глобальный экземпляр процессора
panorama_processor = PanoramaProcessor() 