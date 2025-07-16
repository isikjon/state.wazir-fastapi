/**
 * JavaScript для обработки множественной загрузки 360° панорам в админке
 */

let multipleCurrentEntityId = null;
let multipleCurrentEntityType = null; // 'property' или 'service-card'
let multipleSelectedFiles = [];
let multipleUploadMode = 'file'; // 'file' или 'url'

$(document).ready(function() {
    // Переключение между табами
    $('#upload-files-tab').on('click', function() {
        switchToMultipleUploadMode('file');
    });

    $('#upload-urls-tab').on('click', function() {
        switchToMultipleUploadMode('url');
    });

    // Обработка выбора множественных файлов
    $(document).on('change', '#panorama-files', function(e) {
        console.log('Файлы выбраны:', e.target.files.length);
        handleMultipleFileSelect(e.target.files);
    });

    // Обработка клика на область загрузки файлов
    $(document).on('click', '#file-drop-area', function(e) {
        e.preventDefault();
        console.log('Клик по области загрузки файлов');
        
        const fileInput = $('#panorama-files');
        console.log('Input элемент найден:', fileInput.length > 0);
        
        if (fileInput.length > 0) {
            fileInput[0].click();
            console.log('Клик по input выполнен');
        } else {
            console.error('Input элемент #panorama-files не найден!');
        }
    });

    // Обработка drag & drop для множественных файлов
    $(document).on('dragover', '#file-drop-area', function(e) {
        e.preventDefault();
        $(this).addClass('border-blue-400 bg-blue-50');
    });

    $(document).on('dragleave', '#file-drop-area', function(e) {
        e.preventDefault();
        $(this).removeClass('border-blue-400 bg-blue-50');
    });

    $(document).on('drop', '#file-drop-area', function(e) {
        e.preventDefault();
        $(this).removeClass('border-blue-400 bg-blue-50');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            handleMultipleFileSelect(files);
        }
    });

    // Открытие модального окна множественной загрузки панорам
    $(document).on('click', '.upload-multiple-panoramas-btn', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log('Кнопка множественной загрузки нажата');
        
        multipleCurrentEntityId = $(this).data('entity-id');
        multipleCurrentEntityType = $(this).data('entity-type');
        
        console.log('Entity ID:', multipleCurrentEntityId, 'Type:', multipleCurrentEntityType);
        
        const modal = $('#multiple-panoramas-modal');
        console.log('Модальное окно найдено:', modal.length > 0);
        
        modal.removeClass('hidden');
        
        // Проверяем, что все элементы на месте после открытия модального окна
        setTimeout(function() {
            const dropArea = $('#file-drop-area');
            const fileInput = $('#panorama-files');
            const fileUploadSection = $('#file-upload-section');
            
            console.log('Drop area найдена:', dropArea.length > 0);
            console.log('File input найден:', fileInput.length > 0);
            console.log('File upload section найдена:', fileUploadSection.length > 0);
            
            // Выводим HTML структуру для отладки
            if (dropArea.length === 0) {
                console.log('HTML модального окна:', $('#multiple-panoramas-modal').html());
            }
        }, 100);
        
        // Сброс формы
        resetMultipleModal();
    });

    // Закрытие модального окна
    $(document).on('click', '.close-multiple-panoramas-modal, #multiple-panoramas-modal-backdrop', function(e) {
        if (e.target === this) {
            $('#multiple-panoramas-modal').addClass('hidden');
            resetMultipleModal();
        }
    });

    // Удаление файла из списка
    $(document).on('click', '.remove-file-btn', function() {
        const index = $(this).data('file-index');
        removeFileFromList(index);
    });

    // Добавление поля URL
    $('#add-url-field').on('click', function() {
        addUrlField();
    });

    // Удаление поля URL
    $(document).on('click', '.remove-url-btn', function() {
        $(this).closest('.url-input-group').remove();
        updateUrlFieldsIndexes();
    });

    // Загрузка панорам
    $('#upload-multiple-panoramas-btn').on('click', function() {
        if (multipleUploadMode === 'file') {
            uploadMultipleFiles();
        } else {
            uploadMultipleUrls();
        }
    });
});

function switchToMultipleUploadMode(mode) {
    multipleUploadMode = mode;
    
    if (mode === 'file') {
        $('#upload-files-tab').addClass('border-blue-500 text-blue-600 font-medium').removeClass('border-transparent text-gray-500');
        $('#upload-urls-tab').addClass('border-transparent text-gray-500').removeClass('border-blue-500 text-blue-600 font-medium');
        $('#file-upload-section').removeClass('hidden');
        $('#url-upload-section').addClass('hidden');
    } else {
        $('#upload-urls-tab').addClass('border-blue-500 text-blue-600 font-medium').removeClass('border-transparent text-gray-500');
        $('#upload-files-tab').addClass('border-transparent text-gray-500').removeClass('border-blue-500 text-blue-600 font-medium');
        $('#url-upload-section').removeClass('hidden');
        $('#file-upload-section').addClass('hidden');
    }
}

function handleMultipleFileSelect(files) {
    if (!files || files.length === 0) return;
    
    // Проверяем общее количество файлов (максимум 10)
    if (multipleSelectedFiles.length + files.length > 10) {
        alert('Максимум 10 панорам за одну загрузку');
        return;
    }
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Проверка типа файла
        if (!file.type.startsWith('image/')) {
            alert(`Файл ${file.name}: должен быть изображением`);
            continue;
        }
        
        // Проверка размера файла (300MB)
        if (file.size > 300 * 1024 * 1024) {
            alert(`Файл ${file.name}: превышает лимит 300 МБ`);
            continue;
        }
        
        multipleSelectedFiles.push({
            file: file,
            name: file.name,
            size: file.size,
            notes: ''
        });
    }
    
    updateFilesList();
}

function removeFileFromList(index) {
    multipleSelectedFiles.splice(index, 1);
    updateFilesList();
}

function updateFilesList() {
    const container = $('#selected-files-list');
    container.empty();
    
    if (multipleSelectedFiles.length === 0) {
        container.html('<p class="text-gray-500 text-center py-4">Файлы не выбраны</p>');
        return;
    }
    
    multipleSelectedFiles.forEach((fileData, index) => {
        const fileItem = $(`
            <div class="file-item border rounded-lg p-3 mb-2">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <div class="font-medium text-sm">${fileData.name}</div>
                        <div class="text-xs text-gray-500">${formatFileSize(fileData.size)}</div>
                    </div>
                    <button type="button" class="remove-file-btn text-red-500 hover:text-red-700 ml-2" data-file-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="mt-2">
                    <input type="text" class="form-input text-sm" placeholder="Комментарий (опционально)" 
                           onchange="updateFileNotes(${index}, this.value)">
                </div>
            </div>
        `);
        container.append(fileItem);
    });
    
    // Обновляем счетчик
    $('#selected-files-count').text(`Выбрано файлов: ${multipleSelectedFiles.length}/10`);
}

function updateFileNotes(index, notes) {
    if (multipleSelectedFiles[index]) {
        multipleSelectedFiles[index].notes = notes;
    }
}

function addUrlField() {
    const urlFields = $('#url-fields-container');
    const index = urlFields.children().length;
    
    if (index >= 10) {
        alert('Максимум 10 панорам за одну операцию');
        return;
    }
    
    const urlField = $(`
        <div class="url-input-group border rounded-lg p-3 mb-2">
            <div class="flex items-center gap-2 mb-2">
                <input type="url" class="form-input flex-1" placeholder="https://kuula.co/share/... или другая ссылка" 
                       name="panorama_urls[]" required>
                <button type="button" class="remove-url-btn text-red-500 hover:text-red-700">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <input type="text" class="form-input text-sm" placeholder="Комментарий (опционально)" 
                   name="panorama_notes[]">
        </div>
    `);
    
    urlFields.append(urlField);
    updateUrlFieldsIndexes();
}

function updateUrlFieldsIndexes() {
    $('#url-fields-container .url-input-group').each(function(index) {
        $(this).find('input[name="panorama_urls[]"]').attr('data-index', index);
        $(this).find('input[name="panorama_notes[]"]').attr('data-index', index);
    });
    
    const count = $('#url-fields-container .url-input-group').length;
    $('#url-fields-count').text(`Полей URL: ${count}/10`);
}

function uploadMultipleFiles() {
    if (multipleSelectedFiles.length === 0) {
        alert('Пожалуйста, выберите файлы для загрузки');
        return;
    }
    
    const formData = new FormData();
    
    // Добавляем файлы
    multipleSelectedFiles.forEach((fileData, index) => {
        formData.append('files', fileData.file);
        formData.append('notes', fileData.notes || '');
    });
    
    // Показываем прогресс
    $('#upload-progress').removeClass('hidden');
    updateProgress(0);
    
    // Отключаем кнопку загрузки
    $('#upload-multiple-panoramas-btn').prop('disabled', true);
    
    // Определяем URL эндпоинта
    let uploadUrl;
    if (multipleCurrentEntityType === 'property') {
        uploadUrl = `/api/v1/admin/properties/${multipleCurrentEntityId}/panoramas/upload`;
    } else if (multipleCurrentEntityType === 'service-card') {
        uploadUrl = `/api/v1/admin/service-cards/${multipleCurrentEntityId}/panoramas/upload`;
    } else {
        alert('Неизвестный тип объекта');
        return;
    }
    
    // Создаем XMLHttpRequest для отслеживания прогресса
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            updateProgress(percentComplete);
        }
    });
    
    xhr.addEventListener('load', function() {
        if (xhr.status === 200) {
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.success) {
                    let message = `Успешно загружено ${response.total_uploaded} панорам`;
                    if (response.errors && response.errors.length > 0) {
                        message += `\n\nОшибки:\n${response.errors.join('\n')}`;
                    }
                    alert(message);
                    $('#multiple-panoramas-modal').addClass('hidden');
                    location.reload();
                } else {
                    alert('Ошибка: ' + (response.error || 'Неизвестная ошибка'));
                }
            } catch (e) {
                alert('Ошибка обработки ответа сервера');
            }
        } else {
            alert('Ошибка загрузки файлов');
        }
        
        $('#upload-multiple-panoramas-btn').prop('disabled', false);
        $('#upload-progress').addClass('hidden');
    });
    
    xhr.addEventListener('error', function() {
        alert('Произошла ошибка при загрузке файлов');
        $('#upload-multiple-panoramas-btn').prop('disabled', false);
        $('#upload-progress').addClass('hidden');
    });
    
    xhr.open('POST', uploadUrl);
    xhr.send(formData);
}

function uploadMultipleUrls() {
    const urlInputs = $('#url-fields-container input[name="panorama_urls[]"]');
    const noteInputs = $('#url-fields-container input[name="panorama_notes[]"]');
    
    const urls = [];
    const notes = [];
    
    urlInputs.each(function() {
        const url = $(this).val().trim();
        if (url) {
            urls.push(url);
        }
    });
    
    noteInputs.each(function() {
        notes.push($(this).val().trim());
    });
    
    if (urls.length === 0) {
        alert('Пожалуйста, укажите хотя бы один URL панорамы');
        return;
    }
    
    // Определяем URL эндпоинта
    let uploadUrl;
    if (multipleCurrentEntityType === 'property') {
        uploadUrl = `/api/v1/admin/properties/${multipleCurrentEntityId}/panoramas/url`;
    } else if (multipleCurrentEntityType === 'service-card') {
        uploadUrl = `/api/v1/admin/service-cards/${multipleCurrentEntityId}/panoramas/url`;
    } else {
        alert('Неизвестный тип объекта');
        return;
    }
    
    const formData = new FormData();
    urls.forEach(url => formData.append('urls', url));
    notes.forEach(note => formData.append('notes', note));
    
    fetch(uploadUrl, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let message = `Успешно добавлено ${data.total_added} панорам`;
            if (data.errors && data.errors.length > 0) {
                message += `\n\nОшибки:\n${data.errors.join('\n')}`;
            }
            alert(message);
            $('#multiple-panoramas-modal').addClass('hidden');
            location.reload();
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка при добавлении панорам по URL:', error);
        alert('Произошла ошибка при добавлении панорам');
    });
}

function resetMultipleModal() {
    multipleSelectedFiles = [];
    updateFilesList();
    
    // Очищаем URL поля
    $('#url-fields-container').empty();
    addUrlField(); // Добавляем одно поле по умолчанию
    
    $('#upload-progress').addClass('hidden');
    updateProgress(0);
    
    // Переключение на режим загрузки файлов
    switchToMultipleUploadMode('file');
}

function updateProgress(percent) {
    $('#progress-percent').text(Math.round(percent) + '%');
    $('#progress-bar').css('width', percent + '%');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}