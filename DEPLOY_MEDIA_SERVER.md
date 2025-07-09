# Развертывание медиа-сервера

## 🚀 Инструкция по настройке медиа-сервера для загрузки панорам

### 1. Файлы для загрузки на сервер `https://wazir.kg/state/`

#### Замените файл `.htaccess` содержимым из `media_server_htaccess`
```bash
# Скопируйте содержимое файла media_server_htaccess в .htaccess на сервере
```

#### Замените файл `upload.php` содержимым из `media_server_upload.php`
```bash
# Скопируйте содержимое файла media_server_upload.php в upload.php на сервере
```

### 2. Проверка настроек сервера

После загрузки файлов проверьте:

#### Проверка работы медиа-сервера:
```bash
curl -X GET "https://wazir.kg/state/upload.php?ping"
```

Ожидаемый ответ:
```json
{
  "status": "success",
  "message": "Media server is working",
  "version": "4.0 - Fully open access",
  "cors_enabled": true,
  "max_file_size": "100MB"
}
```

#### Проверка CORS заголовков:
```bash
curl -I -X OPTIONS "https://wazir.kg/state/upload.php"
```

Должны присутствовать заголовки:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With, X-Forwarded-For`

### 3. Структура директорий

После первой загрузки файлов будут созданы директории:

```
state/
├── uploads/
│   ├── {property_id}/          # Обычные изображения
│   │   ├── original/
│   │   ├── large/
│   │   ├── medium/
│   │   └── thumb/
│   └── panoramas/
│       └── {property_id}/      # 360° панорамы
│           ├── original/
│           ├── optimized/
│           ├── preview/
│           └── thumbnails/
├── upload.php                  # Загрузка файлов
├── image.php                   # Отдача изображений
├── delete.php                  # Удаление файлов
├── debug_upload.php           # Отладка
└── .htaccess                  # Настройки сервера
```

### 4. Настройки PHP

Убедитесь что в php.ini установлены следующие параметры:
```ini
upload_max_filesize = 100M
post_max_size = 100M
max_execution_time = 300
max_input_time = 300
memory_limit = 256M
```

### 5. Права доступа

Установите правильные права доступа:
```bash
chmod 755 /path/to/state/
chmod 644 /path/to/state/.htaccess
chmod 644 /path/to/state/upload.php
chmod 644 /path/to/state/image.php
chmod 644 /path/to/state/delete.php
chmod 755 /path/to/state/uploads/
```

### 6. Что изменено

#### В `.htaccess`:
- ✅ Убраны все ограничения на PHP файлы
- ✅ Добавлены CORS заголовки для всех типов файлов
- ✅ Увеличены лимиты загрузки до 100MB
- ✅ Отключен mod_security если включен

#### В `upload.php`:
- ✅ Добавлены полностью открытые CORS заголовки
- ✅ Улучшена обработка OPTIONS запросов
- ✅ Исправлена обработка панорам с `panorama_type=true`
- ✅ Добавлена детальная отладочная информация
- ✅ Улучшена обработка ошибок

### 7. Тестирование

После развертывания протестируйте:

1. **Ping тест:**
   ```bash
   curl "https://wazir.kg/state/upload.php?ping"
   ```

2. **CORS тест:**
   ```bash
   curl -H "Origin: http://localhost:8000" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS \
        "https://wazir.kg/state/upload.php"
   ```

3. **Загрузка панорамы через ваше приложение**

### 8. Безопасность

⚠️ **ВНИМАНИЕ**: Эта конфигурация полностью открывает доступ к PHP файлам для всех источников. 

Для продакшена рекомендуется:
- Ограничить `Access-Control-Allow-Origin` конкретными доменами
- Добавить аутентификацию для загрузки файлов  
- Настроить rate limiting
- Добавить валидацию типов файлов

### 9. Мониторинг

Проверяйте логи сервера:
```bash
tail -f /var/log/apache2/error.log
tail -f /var/log/apache2/access.log
```

## 🎉 Готово!

После выполнения всех шагов ваша система загрузки 360° панорам должна работать корректно. 