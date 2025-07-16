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
        
        // Показываем модальное окно
        console.log('📋 До изменения классов:', modal.attr('class'));
        modal.removeClass('hidden').addClass('show');
        console.log('📋 После изменения классов:', modal.attr('class'));
        console.log('💡 Модальное окно должно быть видимым');
        
        // Загружаем текущие панорамы
        setTimeout(function() {
            loadCurrentPanoramas();
        }, 100);
        
        // Сброс формы
        resetMultipleModal();
    });

    // Закрытие модального окна только по кнопкам, НЕ по клику вне области
    $(document).on('click', '.close-multiple-panoramas-modal', function(e) {
        $('#multiple-panoramas-modal').removeClass('show').addClass('hidden');
            resetMultipleModal();
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
    showUploadProgress();
    updateUploadProgress(0, 'Подготовка к загрузке...');
    
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
        hideUploadProgress();
        uploadBtn.prop('disabled', false).html('Загрузить панорамы');
        return;
    }
    
    // Создаем XMLHttpRequest для отслеживания прогресса
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            updateUploadProgress(percentComplete, 'Загрузка файлов...');
        }
    });
    
    xhr.addEventListener('load', function() {
        if (xhr.status === 200) {
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.success) {
                    updateUploadProgress(100, 'Загрузка завершена!');
                    
                    setTimeout(() => {
                    let message = `Успешно загружено ${response.total_uploaded} панорам`;
                    if (response.errors && response.errors.length > 0) {
                        message += `\n\nОшибки:\n${response.errors.join('\n')}`;
                    }
                    alert(message);
                        
                        // Обновляем список текущих панорам
                        loadCurrentPanoramas();
                        
                        // Обновляем статус 360° тура на странице
                        updatePagePanoramaStatus();
                        
                        // Сбрасываем форму
                        resetMultipleModal();
                        hideUploadProgress();
                    }, 1000);
                } else {
                    alert('Ошибка: ' + (response.error || 'Неизвестная ошибка'));
                    hideUploadProgress();
                }
            } catch (e) {
                alert('Ошибка обработки ответа сервера');
                hideUploadProgress();
            }
        } else {
            alert('Ошибка загрузки файлов');
            hideUploadProgress();
        }
        
        // Восстанавливаем кнопку
        uploadBtn.prop('disabled', false);
        uploadBtn.html('Загрузить панорамы');
    });
    
    xhr.addEventListener('error', function() {
        alert('Произошла ошибка при загрузке файлов');
        // Восстанавливаем кнопку
        uploadBtn.prop('disabled', false);
        uploadBtn.html('Загрузить панорамы');
        hideUploadProgress();
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
    
    // Показываем прогресс
    showUploadProgress();
    updateUploadProgress(0, 'Обработка URL...');
    
    // Определяем URL эндпоинта
    let uploadUrl;
    if (multipleCurrentEntityType === 'property') {
        uploadUrl = `/api/v1/admin/properties/${multipleCurrentEntityId}/panoramas/url`;
    } else if (multipleCurrentEntityType === 'service-card') {
        uploadUrl = `/api/v1/admin/service-cards/${multipleCurrentEntityId}/panoramas/url`;
    } else {
        alert('Неизвестный тип объекта');
        hideUploadProgress();
        return;
    }
    
    const formData = new FormData();
    urls.forEach(url => formData.append('urls', url));
    notes.forEach(note => formData.append('notes', note));
    
    fetch(uploadUrl, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        updateUploadProgress(50, 'Обработка ответа...');
        return response.json();
    })
    .then(data => {
        updateUploadProgress(100, 'Завершено!');
        
        setTimeout(() => {
        if (data.success) {
            let message = `Успешно добавлено ${data.total_added} панорам`;
            if (data.errors && data.errors.length > 0) {
                message += `\n\nОшибки:\n${data.errors.join('\n')}`;
            }
            alert(message);
                
                // Обновляем список текущих панорам
                loadCurrentPanoramas();
                
                // Обновляем статус 360° тура на странице
                updatePagePanoramaStatus();
                
                // Сбрасываем форму
                resetMultipleModal();
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
            hideUploadProgress();
        }, 1000);
    })
    .catch(error => {
        console.error('Ошибка при добавлении панорам по URL:', error);
        alert('Произошла ошибка при добавлении панорам');
        hideUploadProgress();
    });
}

// Функция для обновления статуса 360° тура на странице
function updatePagePanoramaStatus() {
    if (!multipleCurrentEntityId || !multipleCurrentEntityType) {
        return;
    }
    
    // Определяем API URL для получения обновленной информации
    let apiUrl;
    if (multipleCurrentEntityType === 'property') {
        apiUrl = `/api/v1/admin/properties/${multipleCurrentEntityId}/media`;
    } else if (multipleCurrentEntityType === 'service-card') {
        apiUrl = `/api/v1/admin/service-cards/${multipleCurrentEntityId}/media`;
    } else {
        return;
    }
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.panoramas) {
                const panoramasCount = data.panoramas.length;
                
                // Находим соответствующую строку в таблице
                let tableRow;
                if (multipleCurrentEntityType === 'property') {
                    tableRow = $(`tr[data-id="${multipleCurrentEntityId}"]`);
                } else {
                    // Для service cards ищем по data-id атрибуту строки
                    tableRow = $(`tr[data-id="${multipleCurrentEntityId}"]`);
                }
                
                if (tableRow.length > 0) {
                    // Находим ячейку с 360° туром
                    let tourCell;
                    if (multipleCurrentEntityType === 'property') {
                        tourCell = tableRow.find('td').eq(7); // Для properties - 8-я колонка (индекс 7)
                    } else if (multipleCurrentEntityType === 'service-card') {
                        tourCell = tableRow.find('td').eq(5); // Для service cards - 6-я колонка (индекс 5)
                    }
                    
                    if (tourCell && tourCell.length > 0) {
                        // Обновляем содержимое ячейки
                        if (panoramasCount > 0) {
                            tourCell.html(`<span class="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Есть (${panoramasCount})</span>`);
                        } else {
                            tourCell.html(`<span class="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">Нет</span>`);
                        }
                    }
                }
            }
        })
        .catch(error => {
            console.error('Ошибка обновления статуса панорам на странице:', error);
        });
}

function showUploadProgress() {
    $('#upload-progress').removeClass('hidden');
}

function hideUploadProgress() {
    $('#upload-progress').addClass('hidden');
}

function updateUploadProgress(percent, status) {
    $('#progress-percent').text(Math.round(percent) + '%');
    $('#progress-bar').css('width', percent + '%');
    $('#upload-status').text(status || 'Загрузка...');
    
    // Обновляем статус в заголовке
    if (percent === 100) {
        $('.progress-status').text('Загрузка завершена!');
    } else if (percent > 0) {
        $('.progress-status').text('Загрузка панорам...');
    } else {
        $('.progress-status').text('Подготовка...');
    }
}

function resetMultipleModal() {
    multipleSelectedFiles = [];
    updateFilesList();
    
    // Очищаем URL поля
    $('#url-fields-container').empty();
    if ($('#add-url-field').length > 0) {
        addUrlField(); // Добавляем одно поле по умолчанию если есть кнопка
    }
    
    hideUploadProgress();
    updateUploadProgress(0, 'Подготовка к загрузке...');
    
    // Переключение на режим загрузки файлов
    switchToMultipleUploadMode('file');
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
        // Обновляем заголовок секции
        $('#current-panoramas-section h3').html(`
            <i class="fas fa-vr-cardboard mr-2"></i>Текущие панорамы (0)
        `);
        return;
    }
    
    const panoramas = data.panoramas;
    let html = '';
    
    panoramas.forEach((panorama, index) => {
        const thumbnailUrl = panorama.thumbnail_url || panorama.preview_url || '/static/img/panorama-placeholder.jpg';
        const uploadDate = panorama.uploaded_at ? new Date(panorama.uploaded_at).toLocaleDateString('ru-RU') : 'Неизвестно';
        const notes = panorama.notes || 'Без комментария';
        
        html += `
            <div class="panorama-item">
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
                <button type="button" class="delete-panorama-btn" data-panorama-id="${panorama.id}">
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
    
    // Показываем индикатор удаления
    const btn = $(this);
    const originalHtml = btn.html();
    btn.html('<i class="fas fa-spinner fa-spin mr-1"></i>Удаление...').prop('disabled', true);
    
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
            btn.html(originalHtml).prop('disabled', false);
        }
    })
    .catch(error => {
        console.error('Ошибка удаления панорамы:', error);
        alert('Произошла ошибка при удалении панорамы');
        btn.html(originalHtml).prop('disabled', false);
    });
});

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}