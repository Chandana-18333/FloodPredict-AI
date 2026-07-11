import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = 'data/floodsense.db'

def init_database():
    print("Initializing database...")
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'User'
    )
    ''')
    
    # 2. Create ML Models Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ml_models (
        model_id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        algorithm_type TEXT NOT NULL,
        accuracy REAL NOT NULL,
        model_file TEXT NOT NULL
    )
    ''')
    
    # 3. Create Weather Data Table (incorporating detailed features for standard scaler)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weather_data (
        data_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        temperature REAL NOT NULL,
        humidity REAL NOT NULL,
        cloud_cover REAL NOT NULL,
        annual_rainfall REAL NOT NULL,
        jan_feb REAL NOT NULL,
        mar_may REAL NOT NULL,
        jun_sep REAL NOT NULL,
        oct_dec REAL NOT NULL,
        avg_june REAL NOT NULL,
        sub_index REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')
    
    # 4. Create Prediction Results Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prediction_results (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_id INTEGER NOT NULL,
        model_id INTEGER NOT NULL,
        flood_result INTEGER NOT NULL,
        flood_probability REAL NOT NULL,
        prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(data_id) REFERENCES weather_data(data_id),
        FOREIGN KEY(model_id) REFERENCES ml_models(model_id)
    )
    ''')
    
    # Pre-populate ML models metadata
    cursor.execute("SELECT COUNT(*) FROM ml_models")
    if cursor.fetchone()[0] == 0:
        print("Inserting default model metadata...")
        cursor.execute('''
        INSERT INTO ml_models (model_name, algorithm_type, accuracy, model_file)
        VALUES ('Random Forest', 'Classification', 96.55, 'models/flood_model.joblib')
        ''')
    
    # Pre-populate a default administrator and a default user
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("Inserting default user accounts...")
        admin_pass = generate_password_hash("admin123")
        user_pass = generate_password_hash("user123")
        
        cursor.execute('''
        INSERT INTO users (name, email, password, role)
        VALUES ('System Administrator', 'admin@floodsense.ai', ?, 'Admin')
        ''', (admin_pass,))
        
        cursor.execute('''
        INSERT INTO users (name, email, password, role)
        VALUES ('John Doe', 'john@gmail.com', ?, 'User')
        ''', (user_pass,))
        
    conn.commit()
    conn.close()
    print("Database initialized successfully at database path.")

if __name__ == '__main__':
    init_database()
