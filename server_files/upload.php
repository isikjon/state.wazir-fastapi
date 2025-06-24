<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

function generateId() {
    return sprintf('%04x-%04x-%04x-%04x', 
        mt_rand(0, 0xffff), mt_rand(0, 0xffff), 
        mt_rand(0, 0xffff), mt_rand(0, 0xffff)
    );
}

function resizeImage($source, $destination, $width, $height, $quality = 85) {
    $info = getimagesize($source);
    $mime = $info['mime'];
    
    switch ($mime) {
        case 'image/jpeg':
            $image = imagecreatefromjpeg($source);
            break;
        case 'image/png':
            $image = imagecreatefrompng($source);
            break;
        case 'image/webp':
            $image = imagecreatefromwebp($source);
            break;
        default:
            return false;
    }
    
    $original_width = imagesx($image);
    $original_height = imagesy($image);
    
    // Вычисляем пропорции
    $ratio = min($width / $original_width, $height / $original_height);
    $new_width = $original_width * $ratio;
    $new_height = $original_height * $ratio;
    
    $new_image = imagecreatetruecolor($new_width, $new_height);
    
    // Сохраняем прозрачность для PNG
    if ($mime == 'image/png') {
        imagealphablending($new_image, false);
        imagesavealpha($new_image, true);
        $transparent = imagecolorallocatealpha($new_image, 255, 255, 255, 127);
        imagefill($new_image, 0, 0, $transparent);
    }
    
    imagecopyresampled($new_image, $image, 0, 0, 0, 0, $new_width, $new_height, $original_width, $original_height);
    
    // Создаем директорию если не существует
    $dir = dirname($destination);
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    
    $result = imagejpeg($new_image, $destination, $quality);
    
    imagedestroy($image);
    imagedestroy($new_image);
    
    return $result;
}

// Проверка связи
if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_GET['ping'])) {
    echo json_encode([
        'status' => 'success',
        'message' => 'Media server is working',
        'timestamp' => time(),
        'server' => $_SERVER['SERVER_NAME'],
        'version' => '2.0 - Fixed multiple files support'
    ]);
    exit;
}

// Загрузка файлов
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Проверяем наличие files и property_id
    if (empty($_FILES) || !isset($_POST['property_id'])) {
        echo json_encode([
            'error' => 'Missing files or property_id',
            'debug' => [
                'files_keys' => array_keys($_FILES),
                'post_keys' => array_keys($_POST),
                'property_id_exists' => isset($_POST['property_id'])
            ]
        ]);
        exit;
    }
    
    $property_id = $_POST['property_id'];
    $base_url = 'https://wazir.kg/state';
    $upload_dir = "uploads/{$property_id}/";
    
    // Создаем директории
    $directories = ['original', 'large', 'medium', 'thumb'];
    foreach ($directories as $dir) {
        if (!is_dir($upload_dir . $dir)) {
            mkdir($upload_dir . $dir, 0755, true);
        }
    }
    
    $uploaded_files = [];
    
    // ИСПРАВЛЕНИЕ: Проверяем разные варианты имен полей для файлов
    $files_field = null;
    if (isset($_FILES['images[]'])) {
        $files_field = 'images[]';
    } elseif (isset($_FILES['images'])) {
        $files_field = 'images';
    } else {
        // Берем первое доступное поле с файлами
        $files_keys = array_keys($_FILES);
        if (!empty($files_keys)) {
            $files_field = $files_keys[0];
        }
    }
    
    if (!$files_field) {
        echo json_encode([
            'error' => 'No files field found',
            'debug' => [
                'available_fields' => array_keys($_FILES),
                'expected_fields' => ['images[]', 'images']
            ]
        ]);
        exit;
    }
    
    $files = $_FILES[$files_field];
    
    // Обрабатываем файлы в зависимости от структуры
    if (is_array($files['name'])) {
        // Множественные файлы
        $file_count = count($files['name']);
        for ($i = 0; $i < $file_count; $i++) {
            if ($files['error'][$i] === UPLOAD_ERR_OK) {
                $file_id = generateId();
                $tmp_name = $files['tmp_name'][$i];
                $original_name = $files['name'][$i];
                
                // Проверяем тип файла
                $allowed_types = ['image/jpeg', 'image/png', 'image/webp'];
                $file_type = mime_content_type($tmp_name);
                
                if (!in_array($file_type, $allowed_types)) {
                    continue;
                }
                
                $file_extension = 'jpg';
                
                // Размеры для разных версий
                $sizes = [
                    'original' => null, // Оригинальный размер
                    'large' => [1200, 900],
                    'medium' => [800, 600],
                    'thumb' => [300, 200]
                ];
                
                $file_urls = [];
                
                foreach ($sizes as $size_name => $dimensions) {
                    $filename = "{$file_id}.{$file_extension}";
                    $filepath = $upload_dir . $size_name . '/' . $filename;
                    
                    if ($size_name === 'original') {
                        // Сохраняем оригинал
                        if (move_uploaded_file($tmp_name, $filepath)) {
                            $file_urls[$size_name] = "{$base_url}/{$filepath}";
                        }
                    } else {
                        // Создаем ресайз
                        if (resizeImage($upload_dir . 'original/' . $filename, $filepath, $dimensions[0], $dimensions[1])) {
                            $file_urls[$size_name] = "{$base_url}/{$filepath}";
                        }
                    }
                }
                
                if (!empty($file_urls)) {
                    $uploaded_files[] = [
                        'file_id' => $file_id,
                        'original_name' => $original_name,
                        'urls' => $file_urls
                    ];
                }
            }
        }
    } else {
        // Один файл
        if ($files['error'] === UPLOAD_ERR_OK) {
            $file_id = generateId();
            $tmp_name = $files['tmp_name'];
            $original_name = $files['name'];
            
            // Проверяем тип файла
            $allowed_types = ['image/jpeg', 'image/png', 'image/webp'];
            $file_type = mime_content_type($tmp_name);
            
            if (in_array($file_type, $allowed_types)) {
                $file_extension = 'jpg';
                
                // Размеры для разных версий
                $sizes = [
                    'original' => null,
                    'large' => [1200, 900],
                    'medium' => [800, 600],
                    'thumb' => [300, 200]
                ];
                
                $file_urls = [];
                
                foreach ($sizes as $size_name => $dimensions) {
                    $filename = "{$file_id}.{$file_extension}";
                    $filepath = $upload_dir . $size_name . '/' . $filename;
                    
                    if ($size_name === 'original') {
                        if (move_uploaded_file($tmp_name, $filepath)) {
                            $file_urls[$size_name] = "{$base_url}/{$filepath}";
                        }
                    } else {
                        if (resizeImage($upload_dir . 'original/' . $filename, $filepath, $dimensions[0], $dimensions[1])) {
                            $file_urls[$size_name] = "{$base_url}/{$filepath}";
                        }
                    }
                }
                
                if (!empty($file_urls)) {
                    $uploaded_files[] = [
                        'file_id' => $file_id,
                        'original_name' => $original_name,
                        'urls' => $file_urls
                    ];
                }
            }
        }
    }
    
    echo json_encode([
        'status' => 'success',
        'property_id' => $property_id,
        'files' => $uploaded_files,
        'count' => count($uploaded_files),
        'message' => 'Files uploaded successfully',
        'debug' => [
            'files_field_used' => $files_field,
            'is_array' => is_array($files['name']),
            'total_processed' => count($uploaded_files),
            'version' => '2.0'
        ]
    ]);
} else {
    echo json_encode(['error' => 'Only POST method allowed']);
}
?> 