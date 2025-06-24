<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// Отладочная информация
$debug_info = [
    'method' => $_SERVER['REQUEST_METHOD'],
    'files_structure' => $_FILES,
    'post_data' => $_POST,
    'content_type' => $_SERVER['CONTENT_TYPE'] ?? 'not set',
    'timestamp' => date('Y-m-d H:i:s')
];

// Сохраняем отладочную информацию в файл
file_put_contents('debug_upload.log', json_encode($debug_info, JSON_PRETTY_PRINT) . "\n\n", FILE_APPEND);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_FILES) || empty($_FILES) || !isset($_POST['property_id'])) {
        echo json_encode([
            'error' => 'Missing files or property_id',
            'debug' => $debug_info
        ]);
        exit;
    }
    
    $property_id = $_POST['property_id'];
    
    $processed_files = [];
    
    // Проверяем все поля с файлами
    foreach ($_FILES as $field_name => $files) {
        if (is_array($files['name'])) {
            // Множественные файлы
            $file_count = count($files['name']);
            for ($i = 0; $i < $file_count; $i++) {
                if ($files['error'][$i] === UPLOAD_ERR_OK) {
                    $processed_files[] = [
                        'field_name' => $field_name,
                        'index' => $i,
                        'name' => $files['name'][$i],
                        'size' => $files['size'][$i],
                        'type' => $files['type'][$i],
                        'tmp_name' => $files['tmp_name'][$i],
                        'error' => $files['error'][$i]
                    ];
                }
            }
        } else {
            // Один файл
            if ($files['error'] === UPLOAD_ERR_OK) {
                $processed_files[] = [
                    'field_name' => $field_name,
                    'index' => 'single',
                    'name' => $files['name'],
                    'size' => $files['size'],
                    'type' => $files['type'],
                    'tmp_name' => $files['tmp_name'],
                    'error' => $files['error']
                ];
            }
        }
    }
    
    echo json_encode([
        'status' => 'debug_success',
        'property_id' => $property_id,
        'files_received' => count($processed_files),
        'processed_files' => $processed_files,
        'debug' => $debug_info,
        'recommendations' => [
            'total_files_fields' => count($_FILES),
            'files_field_names' => array_keys($_FILES),
            'expected_field_names' => ['images[]', 'images'],
            'message' => 'Check if files are being sent with correct field names'
        ]
    ]);
} else {
    echo json_encode([
        'error' => 'Only POST method allowed',
        'debug' => $debug_info
    ]);
}
?> 