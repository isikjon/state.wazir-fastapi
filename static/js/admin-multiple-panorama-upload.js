/**
 * JavaScript для обработки множественной загрузки 360° панорам в админке
 */

console.log('🚀 admin-multiple-panorama-upload.js загружен');

let multipleCurrentEntityId = null;
let multipleCurrentEntityType = null; // 'property' или 'service-card'
let multipleSelectedFiles = [];
let multipleUploadMode = 'file'; // 'file' или 'url'

$(document).ready(function() {
    console.log('📝 Document ready для admin-multiple-panorama-upload.js');
    
    // Проверяем есть ли кнопки на странице
    const uploadButtons = $('.upload-multiple-panoramas-btn');
    console.log('🔍 Найдено кнопок загрузки панорам:', uploadButtons.length);
    
    // Проверяем есть ли модальное окно
    const modal = $('#multiple-panoramas-modal');
    console.log('🪟 Модальное окно найдено:', modal.length > 0);

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
        console.log('🎯 КЛИК ПО КНОПКЕ ПАНОРАМ!!! Обработчик сработал');
        
        e.preventDefault();
        e.stopPropagation();
        
        multipleCurrentEntityId = $(this).data('entity-id');
        multipleCurrentEntityType = $(this).data('entity-type');
        
        console.log('Entity ID:', multipleCurrentEntityId, 'Type:', multipleCurrentEntityType);
        
        const modal = $('#multiple-panoramas-modal');
        console.log('Модальное окно найдено:', modal.length > 0);
        
        modal.removeClass('hidden');
        
        // Загружаем текущие панорамы
        setTimeout(function() {
            loadCurrentPanoramas();
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
    
    // Отключаем кнопку загрузки и меняем текст
    const uploadBtn = $('#upload-multiple-panoramas-btn');
    uploadBtn.prop('disabled', true);
    uploadBtn.html('<i class="fas fa-spinner fa-spin mr-2"></i>Загружаем...');
    
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
        
        // Восстанавливаем кнопку
        uploadBtn.prop('disabled', false);
        uploadBtn.html('Загрузить панорамы');
        $('#upload-progress').addClass('hidden');
    });
    
    xhr.addEventListener('error', function() {
        alert('Произошла ошибка при загрузке файлов');
        // Восстанавливаем кнопку
        uploadBtn.prop('disabled', false);
        uploadBtn.html('Загрузить панорамы');
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

function loadCurrentPanoramas() {
    if (!multipleCurrentEntityId || !multipleCurrentEntityType) {
        console.log('Нет данных для загрузки панорам');
        return;
    }
    
    // Определяем API URL в зависимости от типа объекта
    let apiUrl;
    if (multipleCurrentEntityType === 'property') {
        apiUrl = `/api/v1/admin/properties/${multipleCurrentEntityId}/media`;
    } else if (multipleCurrentEntityType === 'service-card') {
        apiUrl = `/api/v1/admin/service-cards/${multipleCurrentEntityId}/media`;
    } else {
        console.log('Неизвестный тип объекта для загрузки панорам');
        return;
    }
    
    console.log('Загружаем текущие панорамы с URL:', apiUrl);
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            console.log('Ответ API панорам:', data);
            displayCurrentPanoramas(data);
        })
        .catch(error => {
            console.error('Ошибка загрузки панорам:', error);
            $('#current-panoramas-list').html('<p class="text-gray-500 text-center py-4">Ошибка загрузки панорам</p>');
        });
}

function displayCurrentPanoramas(data) {
    const container = $('#current-panoramas-list');
    
    if (!data.success || !data.panoramas || data.panoramas.length === 0) {
        container.html('<p class="text-gray-500 text-center py-4">Панорамы не найдены</p>');
        return;
    }
    
    const panoramas = data.panoramas;
    let html = '';
    
    panoramas.forEach((panorama, index) => {
        const thumbnailUrl = panorama.thumbnail_url || panorama.preview_url || '/static/img/panorama-placeholder.jpg';
        const uploadDate = panorama.uploaded_at ? new Date(panorama.uploaded_at).toLocaleDateString('ru-RU') : 'Неизвестно';
        const notes = panorama.notes || 'Без комментария';
        
        html += `
            <div class="panorama-item bg-gray-50 border border-gray-200 rounded-lg p-3">
                <div class="aspect-video bg-gray-100 rounded mb-2 overflow-hidden">
                    <img src="${thumbnailUrl}" alt="Панорама ${index + 1}" 
                         class="w-full h-full object-cover" 
                         onerror="this.src='/static/img/panorama-placeholder.jpg'">
                </div>
                <div class="text-xs text-gray-600">
                    <div class="font-medium mb-1">Панорама ${index + 1}</div>
                    <div>Загружена: ${uploadDate}</div>
                    <div class="mt-1 text-gray-500">${notes}</div>
                </div>
                <button type="button" class="delete-panorama-btn mt-2 w-full px-2 py-1 bg-red-100 hover:bg-red-200 text-red-600 text-xs rounded" 
                        data-panorama-id="${panorama.id}">
                    <i class="fas fa-trash mr-1"></i>Удалить
                </button>
            </div>
        `;
    });
    
    container.html(html);
    
    // Обновляем заголовок секции
    $('#current-panoramas-section h3').html(`
        <i class="fas fa-vr-cardboard mr-2"></i>Текущие панорамы (${panoramas.length})
    `);
}

// Обработчик удаления панорамы
$(document).on('click', '.delete-panorama-btn', function() {
    const panoramaId = $(this).data('panorama-id');
    
    if (!confirm('Вы уверены, что хотите удалить эту панораму?')) {
        return;
    }
    
    let deleteUrl;
    if (multipleCurrentEntityType === 'property') {
        deleteUrl = `/api/v1/admin/properties/${multipleCurrentEntityId}/panoramas/${panoramaId}`;
    } else if (multipleCurrentEntityType === 'service-card') {
        deleteUrl = `/api/v1/admin/service-cards/${multipleCurrentEntityId}/panoramas/${panoramaId}`;
    } else {
        alert('Ошибка: неизвестный тип объекта');
        return;
    }
    
    fetch(deleteUrl, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Панорама успешно удалена');
            loadCurrentPanoramas(); // Перезагружаем список
        } else {
            alert('Ошибка удаления: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка удаления панорамы:', error);
        alert('Произошла ошибка при удалении панорамы');
    });
});

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}