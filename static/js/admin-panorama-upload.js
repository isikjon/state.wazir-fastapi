/**
 * JavaScript для обработки загрузки 360° панорам в админке
 */

let currentPropertyId = null;
let selectedFile = null;
let uploadMode = 'file'; // 'file' или 'url'

$(document).ready(function() {
    // Переключение между табами
    $('#upload-tab').on('click', function() {
        switchToUploadMode('file');
    });

    $('#url-tab').on('click', function() {
        switchToUploadMode('url');
    });

    // Обработка выбора файла
    $('#panorama-file').on('change', function(e) {
        handleFileSelect(e.target.files[0]);
    });

    // Обработка drag & drop
    const dropArea = $('.border-dashed').parent();
    
    dropArea.on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('border-blue-400 bg-blue-50');
    });

    dropArea.on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('border-blue-400 bg-blue-50');
    });

    dropArea.on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('border-blue-400 bg-blue-50');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    // Удаление выбранного файла
    $('#remove-file').on('click', function() {
        removeSelectedFile();
    });

    // Открытие модального окна 360°
    $(document).on('click', '.upload-360-btn', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        currentPropertyId = $(this).data('property-id');
        $('#property-id-for-360').val(currentPropertyId);
        $('#upload-360-modal').removeClass('hidden');
        
        // Сброс формы
        resetModal();
        
        // Загружаем существующие данные 360°
        loadExisting360Data(currentPropertyId);
    });

    // Закрытие модального окна
    $(document).on('click', '.close-upload-360-modal, #upload-360-modal-backdrop', function(e) {
        if (e.target === this) {
            $('#upload-360-modal').addClass('hidden');
            resetModal();
        }
    });

    // Сохранение 360°
    $('#save-360-btn').on('click', function() {
        if (uploadMode === 'file') {
            uploadFileMode();
        } else {
            uploadUrlMode();
        }
    });

    // Удаление 360°
    $('#delete-360-btn').on('click', function() {
        if (confirm('Вы уверены, что хотите удалить 360° панораму?')) {
            delete360Panorama();
        }
    });
});

function switchToUploadMode(mode) {
    uploadMode = mode;
    
    if (mode === 'file') {
        $('#upload-tab').addClass('border-blue-500 text-blue-600 font-medium').removeClass('border-transparent text-gray-500');
        $('#url-tab').addClass('border-transparent text-gray-500').removeClass('border-blue-500 text-blue-600 font-medium');
        $('#file-upload-form').removeClass('hidden');
        $('#url-upload-form').addClass('hidden');
    } else {
        $('#url-tab').addClass('border-blue-500 text-blue-600 font-medium').removeClass('border-transparent text-gray-500');
        $('#upload-tab').addClass('border-transparent text-gray-500').removeClass('border-blue-500 text-blue-600 font-medium');
        $('#url-upload-form').removeClass('hidden');
        $('#file-upload-form').addClass('hidden');
    }
}

function handleFileSelect(file) {
    if (!file) return;
    
    // Проверка типа файла
    if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, выберите файл изображения');
        return;
    }
    
    // Проверка размера файла (100MB)
    if (file.size > 100 * 1024 * 1024) {
        alert('Файл слишком большой. Максимальный размер: 100MB');
        return;
    }
    
    selectedFile = file;
    
    // Показываем превью
    const reader = new FileReader();
    reader.onload = function(e) {
        $('#preview-image').attr('src', e.target.result);
        $('#file-name').text(file.name);
        $('#file-size').text(formatFileSize(file.size));
        $('#file-preview').removeClass('hidden');
    };
    reader.readAsDataURL(file);
}

function removeSelectedFile() {
    selectedFile = null;
    $('#file-preview').addClass('hidden');
    $('#panorama-file').val('');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function resetModal() {
    // Сброс всех форм
    removeSelectedFile();
    $('#tour-360-url').val('');
    $('#tour-360-date').val('');
    $('#upload-progress').addClass('hidden');
    $('#existing-panorama-info').addClass('hidden');
    $('#delete-360-btn').addClass('hidden');
    
    // Сброс прогресса
    updateProgress(0);
    
    // Переключение на режим загрузки файла
    switchToUploadMode('file');
}

function loadExisting360Data(propertyId) {
    fetch(`/api/v1/panorama_upload/admin/properties/${propertyId}/360`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data) {
                const panoramaData = data.data;
                $('#360-status').text(panoramaData.status || 'Неизвестно');
                $('#360-file-name').text(panoramaData.file_name || 'Неизвестно');
                $('#360-file-size').text(panoramaData.file_size || 'Неизвестно');
                $('#360-upload-date').text(formatDate(panoramaData.upload_date) || 'Неизвестно');
                
                // Показать информацию о панораме
                $('#existing-360-info').removeClass('hidden');
                $('#360-upload-section').addClass('hidden');
                $('#delete-360-btn').removeClass('hidden');
                
                // Скрыть кнопки загрузки
                $('#save-360-btn').addClass('hidden');
                $('#reset-360-btn').addClass('hidden');
            } else {
                // Показать секцию загрузки
                $('#existing-360-info').addClass('hidden');
                $('#360-upload-section').removeClass('hidden');
                $('#delete-360-btn').addClass('hidden');
                
                // Показать кнопки загрузки
                $('#save-360-btn').removeClass('hidden');
                $('#reset-360-btn').removeClass('hidden');
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке информации о 360°:', error);
            // В случае ошибки показать секцию загрузки
            $('#existing-360-info').addClass('hidden');
            $('#360-upload-section').removeClass('hidden');
            $('#delete-360-btn').addClass('hidden');
            
            // Показать кнопки загрузки
            $('#save-360-btn').removeClass('hidden');
            $('#reset-360-btn').removeClass('hidden');
        });
}

function uploadFileMode() {
    if (!selectedFile) {
        alert('Пожалуйста, выберите файл для загрузки');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Показываем прогресс
    $('#upload-progress').removeClass('hidden');
    updateProgress(0);
    
    // Отключаем кнопку сохранения
    $('#save-360-btn').prop('disabled', true);
    
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
                    alert('360° панорама успешно загружена и обработана!');
                    $('#upload-360-modal').addClass('hidden');
                    location.reload();
                } else {
                    alert('Ошибка: ' + (response.message || 'Неизвестная ошибка'));
                }
            } catch (e) {
                alert('Ошибка обработки ответа сервера');
            }
        } else {
            alert('Ошибка загрузки файла');
        }
        
        $('#save-360-btn').prop('disabled', false);
        $('#upload-progress').addClass('hidden');
    });
    
    xhr.addEventListener('error', function() {
        alert('Произошла ошибка при загрузке файла');
        $('#save-360-btn').prop('disabled', false);
        $('#upload-progress').addClass('hidden');
    });
    
    xhr.open('POST', `/api/v1/panorama_upload/admin/properties/${currentPropertyId}/360/upload`);
    xhr.send(formData);
}

function uploadUrlMode() {
    const tourUrl = $('#tour-360-url').val().trim();
    const tourDate = $('#tour-360-date').val();
    
    if (!tourUrl) {
        alert('Пожалуйста, укажите URL 360° панорамы');
        return;
    }
    
    const formData = new FormData();
    formData.append('tour_360_url', tourUrl);
    if (tourDate) {
        formData.append('tour_360_date', tourDate);
    }
    
    fetch(`/api/v1/panorama_upload/admin/properties/${currentPropertyId}/360`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: tourUrl
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('360° панорама успешно загружена через URL!');
            $('#360-modal').modal('hide');
            loadExisting360Data(currentPropertyId);
        } else {
            alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка при сохранении данных 360°:', error);
        alert('Произошла ошибка при сохранении данных');
    });
}

function delete360Panorama() {
    fetch(`/api/v1/panorama_upload/admin/properties/${currentPropertyId}/360`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('360° панорама успешно удалена!');
            $('#360-modal').modal('hide');
            loadExisting360Data(currentPropertyId);
        } else {
            alert('Ошибка: ' + (data.message || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка при удалении 360°:', error);
        alert('Произошла ошибка при удалении панорамы');
    });
}

function updateProgress(percent) {
    $('#progress-percent').text(Math.round(percent) + '%');
    $('#progress-bar').css('width', percent + '%');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
} 