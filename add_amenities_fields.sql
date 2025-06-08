-- Добавление новых полей удобств в таблицу properties
ALTER TABLE properties 
ADD COLUMN has_elevator BOOLEAN DEFAULT FALSE,
ADD COLUMN has_security BOOLEAN DEFAULT FALSE,
ADD COLUMN has_internet BOOLEAN DEFAULT FALSE,
ADD COLUMN has_air_conditioning BOOLEAN DEFAULT FALSE,
ADD COLUMN has_heating BOOLEAN DEFAULT FALSE,
ADD COLUMN has_yard BOOLEAN DEFAULT FALSE,
ADD COLUMN has_pool BOOLEAN DEFAULT FALSE,
ADD COLUMN has_gym BOOLEAN DEFAULT FALSE,
ADD COLUMN bathroom_type VARCHAR(50),
ADD COLUMN category_id INT;

-- Добавляем внешний ключ для category_id
ALTER TABLE properties 
ADD CONSTRAINT fk_properties_category_id 
FOREIGN KEY (category_id) REFERENCES categories(id); 