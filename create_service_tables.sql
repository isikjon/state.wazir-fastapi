-- Создание таблиц для системы сервисов

-- Таблица категорий сервисов
CREATE TABLE IF NOT EXISTS service_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_service_categories_slug ON service_categories(slug);
CREATE INDEX IF NOT EXISTS idx_service_categories_is_active ON service_categories(is_active);

-- Таблица карточек заведений
CREATE TABLE IF NOT EXISTS service_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    address VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(255),
    image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT 1,
    category_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES service_categories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_service_cards_category ON service_cards(category_id);
CREATE INDEX IF NOT EXISTS idx_service_cards_is_active ON service_cards(is_active);

-- Таблица изображений заведений
CREATE TABLE IF NOT EXISTS service_card_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_card_id INTEGER NOT NULL,
    url VARCHAR(255) NOT NULL,
    is_main BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_card_id) REFERENCES service_cards(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_service_card_images_card ON service_card_images(service_card_id);
CREATE INDEX IF NOT EXISTS idx_service_card_images_main ON service_card_images(is_main);

-- Вставка начальных данных
INSERT OR IGNORE INTO service_categories (title, slug) VALUES 
('Рестораны', 'restaurants'),
('Кафе', 'cafes'),
('Отели', 'hotels'),
('Красота и здоровье', 'beauty-health'),
('Развлечения', 'entertainment'),
('Автосервисы', 'car-services'),
('Магазины', 'shops'),
('Услуги', 'services'); 