<?php
// UPLOAD.PHP для NGINX сервера
// CORS заголовки устанавливаются в nginx конфигурации
// Совместимость с PHP 5.6.40

// Обработка OPTIONS запросов
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Устанавливаем Content-Type для JSON ответов
header('Content-Type: application/json; charset=utf-8');

// Настройки ошибок
error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);

// Функция генерации уникального ID (совместимо с PHP 5.6)
function generateId() {
    return sprintf('%04x-%04x-%04x-%04x', 
        mt_rand(0, 0xffff), mt_rand(0, 0xffff), 
        mt_rand(0, 0xffff), mt_rand(0, 0xffff)
    );
}

// Функция изменения размера изображения (совместимо с PHP 5.6)
function resizeImage($source, $destination, $width, $height, $quality = 85) {
    $info = getimagesize($source);
    if (!$info) return false;
    
    $mime = $info['mime'];
    
    switch ($mime) {
        case 'image/jpeg':
            $image = imagecreatefromjpeg($source);
            break;
        case 'image/png':
            $image = imagecreatefrompng($source);
            break;
        case 'image/webp':
            if (function_exists('imagecreatefromwebp')) {
                $image = imagecreatefromwebp($source);
            } else {
                return false;
            }
            break;
        default:
            return false;
    }
    
    if (!$image) return false;
    
    $original_width = imagesx($image);
    $original_height = imagesy($image);
    
    $ratio = min($width / $original_width, $height / $original_height);
    $new_width = intval($original_width * $ratio);
    $new_height = intval($original_height * $ratio);
    
    $new_image = imagecreatetruecolor($new_width, $new_height);
    
    if ($mime == 'image/png') {
        imagealphablending($new_image, false);
        imagesavealpha($new_image, true);
        $transparent = imagecolorallocatealpha($new_image, 255, 255, 255, 127);
        imagefill($new_image, 0, 0, $transparent);
    }
    
    imagecopyresampled($new_image, $image, 0, 0, 0, 0, $new_width, $new_height, $original_width, $original_height);
    
    $dir = dirname($destination);
    if (!is_dir($dir)) {
        if (!mkdir($dir, 0755, true)) {
            return false;
        }
    }
    
    $result = imagejpeg($new_image, $destination, $quality);
    
    imagedestroy($image);
    imagedestroy($new_image);
    
    return $result;
}

// Обработка ping запросов
if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_GET['ping'])) {
    $response = array(
        'status' => 'success',
        'message' => 'Media server is working',
        'timestamp' => time(),
        'server' => isset($_SERVER['SERVER_NAME']) ? $_SERVER['SERVER_NAME'] : 'unknown',
        'version' => '5.0 - Nginx Compatible',
        'web_server' => 'nginx',
        'php_version' => phpversion(),
        'gd_enabled' => extension_loaded('gd'),
        'webp_support' => function_exists('imagecreatefromwebp'),
        'upload_settings' => array(
            'upload_max_filesize' => ini_get('upload_max_filesize'),
            'post_max_size' => ini_get('post_max_size'),
            'max_execution_time' => ini_get('max_execution_time')
        )
    );
    echo json_encode($response);
    exit;
}

// Основная обработка POST запросов
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    
    // Проверяем наличие файлов и property_id
    if (empty($_FILES) || !isset($_POST['property_id'])) {
        $response = array(
            'status' => 'error',
            'message' => 'Missing files or property_id',
            'debug' => array(
                'files_received' => !empty($_FILES),
                'property_id_received' => isset($_POST['property_id']),
                'files_keys' => !empty($_FILES) ? array_keys($_FILES) : array(),
                'post_keys' => !empty($_POST) ? array_keys($_POST) : array(),
                'method' => $_SERVER['REQUEST_METHOD'],
                'content_type' => isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : 'not set'
            )
        );
        echo json_encode($response);
        exit;
    }
    
    $property_id = $_POST['property_id'];
    $is_panorama = isset($_POST['panorama_type']) && $_POST['panorama_type'] === 'true';
    $base_url = 'https://wazir.kg/state';
    
    // Определяем директории и размеры в зависимости от типа
    if ($is_panorama) {
        $upload_dir = "uploads/panoramas/{$property_id}/";
        $directories = array('original', 'optimized', 'preview', 'thumbnails');
        $sizes = array(
            'original' => null,
            'optimized' => array(2048, 1024),
            'preview' => array(1024, 512), 
            'thumbnails' => array(300, 150)
        );
    } else {
        $upload_dir = "uploads/{$property_id}/";
        $directories = array('original', 'large', 'medium', 'thumb');
        $sizes = array(
            'original' => null,
            'large' => array(1200, 900),
            'medium' => array(800, 600),
            'thumb' => array(300, 200)
        );
    }
    
    // Создаем директории
    foreach ($directories as $dir) {
        $full_dir = $upload_dir . $dir;
        if (!is_dir($full_dir)) {
            if (!mkdir($full_dir, 0755, true)) {
                $response = array(
                    'status' => 'error',
                    'message' => "Cannot create directory: {$full_dir}"
                );
                echo json_encode($response);
                exit;
            }
        }
    }
    
    $uploaded_files = array();
    
    // Определяем поле с файлами
    $files_field = null;
    if (isset($_FILES['images'])) {
        $files_field = 'images';
    } elseif (isset($_FILES['panorama'])) {
        $files_field = 'panorama';
    } else {
        $files_keys = array_keys($_FILES);
        if (!empty($files_keys)) {
            $files_field = $files_keys[0];
        }
    }
    
    if (!$files_field) {
        $response = array(
            'status' => 'error',
            'message' => 'No files field found',
            'debug' => array(
                'available_fields' => array_keys($_FILES),
                'expected_fields' => array('images', 'panorama')
            )
        );
        echo json_encode($response);
        exit;
    }
    
    $files = $_FILES[$files_field];
    
    // Обработка массива файлов
    if (is_array($files['name'])) {
        $file_count = count($files['name']);
        for ($i = 0; $i < $file_count; $i++) {
            if ($files['error'][$i] === UPLOAD_ERR_OK) {
                $file_id = generateId();
                $tmp_name = $files['tmp_name'][$i];
                $original_name = $files['name'][$i];
                
                $allowed_types = array('image/jpeg', 'image/png', 'image/webp');
                $file_type = mime_content_type($tmp_name);
                
                if (!in_array($file_type, $allowed_types)) {
                    continue;
                }
                
                $file_extension = 'jpg';
                $file_urls = array();
                
                // Сначала сохраняем оригинал
                $filename = "{$file_id}.{$file_extension}";
                $original_filepath = $upload_dir . 'original/' . $filename;
                
                if (move_uploaded_file($tmp_name, $original_filepath)) {
                    $file_urls['original'] = "{$base_url}/{$original_filepath}";
                    
                    // Создаем остальные размеры
                    foreach ($sizes as $size_name => $dimensions) {
                        if ($size_name === 'original') continue;
                        
                        $filepath = $upload_dir . $size_name . '/' . $filename;
                        if (resizeImage($original_filepath, $filepath, $dimensions[0], $dimensions[1], $is_panorama ? 95 : 85)) {
                            $file_urls[$size_name] = "{$base_url}/{$filepath}";
                        }
                    }
                    
                    if (!empty($file_urls)) {
                        $uploaded_files[] = array(
                            'file_id' => $file_id,
                            'original_name' => $original_name,
                            'urls' => $file_urls,
                            'type' => $is_panorama ? 'panorama' : 'image'
                        );
                    }
                }
            }
        }
    } else {
        // Обработка одиночного файла
        if ($files['error'] === UPLOAD_ERR_OK) {
            $file_id = generateId();
            $tmp_name = $files['tmp_name'];
            $original_name = $files['name'];
            
            $allowed_types = array('image/jpeg', 'image/png', 'image/webp');
            $file_type = mime_content_type($tmp_name);
            
            if (in_array($file_type, $allowed_types)) {
                $file_extension = 'jpg';
                $file_urls = array();
                
                // Сначала сохраняем оригинал
                $filename = "{$file_id}.{$file_extension}";
                $original_filepath = $upload_dir . 'original/' . $filename;
                
                if (move_uploaded_file($tmp_name, $original_filepath)) {
                    $file_urls['original'] = "{$base_url}/{$original_filepath}";
                    
                    // Создаем остальные размеры
                    foreach ($sizes as $size_name => $dimensions) {
                        if ($size_name === 'original') continue;
                        
                        $filepath = $upload_dir . $size_name . '/' . $filename;
                        if (resizeImage($original_filepath, $filepath, $dimensions[0], $dimensions[1], $is_panorama ? 95 : 85)) {
                            $file_urls[$size_name] = "{$base_url}/{$filepath}";
                        }
                    }
                    
                    if (!empty($file_urls)) {
                        $uploaded_files[] = array(
                            'file_id' => $file_id,
                            'original_name' => $original_name,
                            'urls' => $file_urls,
                            'type' => $is_panorama ? 'panorama' : 'image'
                        );
                    }
                }
            }
        }
    }
    
    // Возвращаем результат
    $response = array(
        'status' => 'success',
        'property_id' => $property_id,
        'files' => $uploaded_files,
        'count' => count($uploaded_files),
        'message' => $is_panorama ? 'Panorama uploaded successfully' : 'Files uploaded successfully',
        'type' => $is_panorama ? 'panorama' : 'images',
        'version' => '5.0',
        'timestamp' => time()
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