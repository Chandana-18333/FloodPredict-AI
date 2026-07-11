from flask import Flask, request, jsonify, render_template, session, redirect, url_for, g
import joblib
import numpy as np
import os
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'floodsense_super_secure_secret_key_2026'

# Paths
MODEL_PATH = 'models/flood_model.joblib'
SCALER_PATH = 'models/scaler.joblib'
DB_PATH = 'data/floodsense.db'

# Load the saved model and scaler dynamically
model = None
scaler = None

def load_model_and_scaler():
    global model, scaler
    if model is None or scaler is None:
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            model = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)
        else:
            print("WARNING: Model or Scaler not found. Run train.py first.")

# Connect to database using Flask application context
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Helper to verify auth session
def is_logged_in():
    return 'user_id' in session

@app.route('/')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid email address or password.')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'User')
        
        if not name or not email or not password:
            return render_template('register.html', error='All fields are required.')
            
        hashed_password = generate_password_hash(password)
        
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                (name, email, hashed_password, role)
            )
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Email address already registered.')
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
def predict():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized. Please login.'}), 401
        
    try:
        load_model_and_scaler()
        if model is None or scaler is None:
            return jsonify({'error': 'Model or Scaler not trained/loaded yet.'}), 500
            
        data = request.get_json()
        
        # Build features DataFrame with matching column names to avoid UserWarning
        feature_names = ['Temp', 'Humidity', 'Cloud Cover', 'ANNUAL', 'Jan-Feb', 'Mar-May', 'Jun-Sep', 'Oct-Dec', 'avgjune', 'sub']
        features_df = pd.DataFrame([[
            float(data['temp']),
            float(data['humidity']),
            float(data['cloud_cover']),
            float(data['annual_rainfall']),
            float(data['jan_feb']),
            float(data['mar_may']),
            float(data['jun_sep']),
            float(data['oct_dec']),
            float(data['avg_june']),
            float(data['sub_index'])
        ]], columns=feature_names)
        
        # Apply scaling
        features_scaled = scaler.transform(features_df)
        
        # Predict target (0 = No Flood, 1 = Flood)
        prediction = model.predict(features_scaled)[0]
        prediction_proba = model.predict_proba(features_scaled)[0]
        
        # 1. Log Weather Data input to SQLite (ER: Weather_Data)
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO weather_data (user_id, temperature, humidity, cloud_cover, annual_rainfall, 
                                     jan_feb, mar_may, jun_sep, oct_dec, avg_june, sub_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            float(data['temp']),
            float(data['humidity']),
            float(data['cloud_cover']),
            float(data['annual_rainfall']),
            float(data['jan_feb']),
            float(data['mar_may']),
            float(data['jun_sep']),
            float(data['oct_dec']),
            float(data['avg_june']),
            float(data['sub_index'])
        ))
        data_id = cursor.lastrowid
        
        # Get active model ID (default is 1 for the pre-populated Random Forest model)
        model_row = cursor.execute('SELECT model_id FROM ml_models ORDER BY model_id DESC LIMIT 1').fetchone()
        model_id = model_row['model_id'] if model_row else 1
        
        # 2. Log Prediction Result to SQLite (ER: Prediction_Result)
        cursor.execute('''
            INSERT INTO prediction_results (data_id, model_id, flood_result, flood_probability)
            VALUES (?, ?, ?, ?)
        ''', (data_id, model_id, int(prediction), float(prediction_proba[1]) * 100))
        
        db.commit()
        
        result = {
            'flood': int(prediction) == 1,
            'flood_probability': float(prediction_proba[1]) * 100,
            'no_flood_probability': float(prediction_proba[0]) * 100
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/history', methods=['GET'])
def history():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
        
    db = get_db()
    logs = db.execute('''
        SELECT 
            pr.prediction_date as date,
            wd.temperature as temp,
            wd.humidity as humidity,
            wd.cloud_cover as cloud_cover,
            wd.annual_rainfall as annual_rainfall,
            wd.jun_sep as jun_sep,
            pr.flood_result as flood,
            pr.flood_probability as flood_probability
        FROM prediction_results pr
        JOIN weather_data wd ON pr.data_id = wd.data_id
        WHERE wd.user_id = ?
        ORDER BY pr.prediction_date DESC
    ''', (session['user_id'],)).fetchall()
    
    history_list = []
    for log in logs:
        history_list.append({
            'date': log['date'],
            'temp': log['temp'],
            'humidity': log['humidity'],
            'cloud_cover': log['cloud_cover'],
            'annual_rainfall': log['annual_rainfall'],
            'jun_sep': log['jun_sep'],
            'flood': bool(log['flood']),
            'flood_probability': log['flood_probability']
        })
        
    return jsonify({'history': history_list})

if __name__ == '__main__':
    # Initial load of model parameters
    load_model_and_scaler()
    app.run(port=5002, debug=True)
