-- Исправление URL панорам для service_cards
-- Добавляем 'panoramas/' в пути к файлам панорам

UPDATE service_cards 
SET 
    tour_360_original_url = REPLACE(tour_360_original_url, '/media/service_card_', '/media/panoramas/service_card_'),
    tour_360_optimized_url = REPLACE(tour_360_optimized_url, '/media/service_card_', '/media/panoramas/service_card_'),
    tour_360_preview_url = REPLACE(tour_360_preview_url, '/media/service_card_', '/media/panoramas/service_card_'),
    tour_360_thumbnail_url = REPLACE(tour_360_thumbnail_url, '/media/service_card_', '/media/panoramas/service_card_')
WHERE 
    tour_360_file_id IS NOT NULL 
    AND (
        tour_360_original_url LIKE '/media/service_card_%'
        OR tour_360_optimized_url LIKE '/media/service_card_%'
        OR tour_360_preview_url LIKE '/media/service_card_%'
        OR tour_360_thumbnail_url LIKE '/media/service_card_%'
    );

-- Аналогично для properties, если нужно
UPDATE properties 
SET 
    tour_360_original_url = REPLACE(tour_360_original_url, '/media/service_card_', '/media/panoramas/service_card_'),
    tour_360_optimized_url = REPLACE(tour_360_optimized_url, '/media/service_card_', '/media/panoramas/service_card_'),
    tour_360_preview_url = REPLACE(tour_360_preview_url, '/media/service_card_', '/media/panoramas/service_card_'),
    tour_360_thumbnail_url = REPLACE(tour_360_thumbnail_url, '/media/service_card_', '/media/panoramas/service_card_')
WHERE 
    tour_360_file_id IS NOT NULL 
    AND (
        tour_360_original_url LIKE '/media/service_card_%'
        OR tour_360_optimized_url LIKE '/media/service_card_%'
        OR tour_360_preview_url LIKE '/media/service_card_%'
        OR tour_360_thumbnail_url LIKE '/media/service_card_%'
    ); 