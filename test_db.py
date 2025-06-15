import pymysql
import time

print("🔍 Проверка подключения к MySQL...")
print("Host: 91.218.141.27")
print("User: wazir")
print("Database: wazir")
print("Port: 3306")
print("-" * 50)

try:
    print("1. Попытка подключения...")
    start_time = time.time()
    
    conn = pymysql.connect(
        host='91.218.141.27',
        user='wazir',
        password='c:ICx9Pr{48y>6BmBc3r',
        database='wazir',
        port=3306,
        connect_timeout=10,
        read_timeout=60,
        write_timeout=60,
        autocommit=True
    )
    
    elapsed = time.time() - start_time
    print(f"✅ Подключение успешно! Время: {elapsed:.2f}s")
    
    print("2. Проверка простого запроса...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"✅ Запрос выполнен: {result}")
    
    print("3. Проверка структуры БД...")
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"✅ Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
    print("4. Проверка таблицы users (быстрый запрос)...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users LIMIT 1")
        count = cursor.fetchone()
        print(f"✅ Найдено пользователей: {count[0]}")
        
    print("5. Поиск пользователя muradnazarov@mail.ru (с индексом)...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, email, role, is_active FROM users WHERE email = %s LIMIT 1", ('muradnazarov@mail.ru',))
        user = cursor.fetchone()
        if user:
            print(f"✅ Пользователь найден: ID={user[0]}, Email={user[1]}, Role={user[2]}, Active={user[3]}")
        else:
            print("❌ Пользователь не найден")
            
    print("6. Проверка всех пользователей с COMPANY ролью...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, email, role FROM users WHERE role = 'COMPANY' LIMIT 5")
        company_users = cursor.fetchall()
        print(f"✅ Найдено компаний: {len(company_users)}")
        for user in company_users:
            print(f"  - ID={user[0]}, Email={user[1]}, Role={user[2]}")
    
    conn.close()
    print("✅ Соединение закрыто")
    
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    print(f"❌ Тип ошибки: {type(e).__name__}") 