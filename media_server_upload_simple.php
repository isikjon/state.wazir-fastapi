<?php
// ПРОСТАЯ ВЕРСИЯ upload.php для PHP 5.6
// НЕ используем CORS заголовки - они в nginx

// Обработка OPTIONS запросов
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// JSON ответ
header('Content-Type: application/json; charset=utf-8');

// Настройки ошибок
error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);

// Функция генерации ID
function generateSimpleId() {
    return sprintf('%04x-%04x-%04x', 
        mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff)
    );
}

// Ping тест
if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_GET['ping'])) {
    $response = array(
        'status' => 'success',
        'message' => 'Media server working',
        'timestamp' => time(),
        'version' => '6.0 - Simple PHP 5.6',
        'web_server' => 'nginx',
        'php_version' => phpversion(),
        'gd_enabled' => extension_loaded('gd')
    );
    echo json_encode($response);
    exit;
}

// POST обработка
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    
    // Проверка базовых данных
    if (empty($_FILES) || !isset($_POST['property_id'])) {
        $response = array(
            'status' => 'error',
            'message' => 'Missing files or property_id',
            'debug' => array(
                'files_received' => !empty($_FILES),
                'property_id_received' => isset($_POST['property_id']),
                'method' => $_SERVER['REQUEST_METHOD']
            )
        );
        echo json_encode($response);
        exit;
    }
    
    $property_id = $_POST['property_id'];
    $is_panorama = isset($_POST['panorama_type']) && $_POST['panorama_type'] === 'true';
    
    // Простая обработка файлов
    $upload_dir = $is_panorama ? "uploads/panoramas/{$property_id}/" : "uploads/{$property_id}/";
    
    // Создаем базовую директорию
    if (!is_dir($upload_dir)) {
        if (!mkdir($upload_dir, 0755, true)) {
            $response = array(
                'status' => 'error',
                'message' => 'Cannot create directory'
            );
            echo json_encode($response);
            exit;
        }
    }
    
    // Создаем поддиректории  
    $subdirs = array('original', 'large', 'medium', 'thumb');
    foreach ($subdirs as $subdir) {
        $full_dir = $upload_dir . $subdir;
        if (!is_dir($full_dir)) {
            mkdir($full_dir, 0755, true);
        }
    }
    
    $uploaded_files = array();
    
    // Простая обработка одного файла
    if (isset($_FILES['images']) || isset($_FILES['panorama'])) {
        $files_field = isset($_FILES['images']) ? 'images' : 'panorama';
        $file = $_FILES[$files_field];
        
        if ($file['error'] === UPLOAD_ERR_OK) {
            $file_id = generateSimpleId();
            $filename = $file_id . '.jpg';
            $original_path = $upload_dir . 'original/' . $filename;
            
            if (move_uploaded_file($file['tmp_name'], $original_path)) {
                $uploaded_files[] = array(
                    'file_id' => $file_id,
                    'original_name' => $file['name'],
                    'urls' => array(
                        'original' => "https://wazir.kg/state/{$original_path}"
                    ),
                    'type' => $is_panorama ? 'panorama' : 'image'
                );
            }
        }
    }
    
    // Ответ
    $response = array(
        'status' => 'success',
        'property_id' => $property_id,
        'files' => $uploaded_files,
        'count' => count($uploaded_files),
        'message' => 'Files uploaded successfully',
        'version' => '6.0'
    );
    echo json_encode($response);
    
} else {
    $response = array(
        'status' => 'error',
        'message' => 'Only GET (ping) and POST methods allowed',
        'method_received' => $_SERVER['REQUEST_METHOD']
    );
    echo json_encode($response);
}
?> 