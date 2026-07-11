import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def run_training_pipeline():
    print("Step 1: Loading weather dataset...")
    df = pd.read_excel('data/flood dataset.xlsx')

    print("Step 2: Resolving missing values...")
    # Fill any empty cells with median values
    for col in df.columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    # Split features and target
    X = df.drop(columns=['flood'])
    y = df['flood']

    # Stratified split to keep label proportions identical
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=93, stratify=y)

    print("Step 3: Applying Standard Scaling to features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("\nStep 4: Training and comparing classification models...")
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight='balanced'),
        "Decision Tree": DecisionTreeClassifier(random_state=42, class_weight='balanced'),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5),
        "XGBoost": XGBClassifier(random_state=42, eval_metric='logloss')
    }

    best_acc = 0.0
    best_model = None
    best_model_name = ""

    for name, clf in models.items():
        # Fit classifier
        clf.fit(X_train_scaled, y_train)
        y_pred = clf.predict(X_test_scaled)
        
        acc = accuracy_score(y_test, y_pred)
        print(f"-> {name} Test Accuracy: {acc * 100:.2f}%")
        
        # Prioritize Random Forest on ties to ensure smooth, dynamic probabilities in the UI
        if acc > best_acc or (acc == best_acc and name == "Random Forest"):
            best_acc = acc
            best_model = clf
            best_model_name = name

    print(f"\nWinner Selected: {best_model_name} with {best_acc * 100:.2f}% accuracy.")
    
    # Print metrics report for the winner
    winner_preds = best_model.predict(X_test_scaled)
    print("\nWinner Performance Report:")
    print(classification_report(y_test, winner_preds))

    print("Step 5: Serializing and saving best model & scaler...")
    os.makedirs('models', exist_ok=True)
    joblib.dump(best_model, 'models/flood_model.joblib')
    joblib.dump(scaler, 'models/scaler.joblib')
    print("[OK] Output model: models/flood_model.joblib")
    print("[OK] Output scaler: models/scaler.joblib")

if __name__ == '__main__':
    run_training_pipeline()
