# import os
# import sys
# import json
# import numpy as np
# import pandas as pd
# import joblib
# import tensorflow as tf

# # Add root to path for shared import
# ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# sys.path.append(ROOT_DIR)

# from agents.shared_preprocessing import preprocess_for_agent2

# # === Agent 1 Paths ===
# AGENT1_DIR = './models/agent1_autoencoder'
# autoencoder = tf.keras.models.load_model(os.path.join(AGENT1_DIR, 'autoencoder_model.keras'))
# scaler_ae = joblib.load(os.path.join(AGENT1_DIR, 'scaler.pkl'))

# # Load all label encoders for Agent 1
# label_encoders = {}
# cat_cols = ['Payment_currency', 'Received_currency', 'Sender_bank_location',
#             'Receiver_bank_location', 'Payment_type', 'Laundering_type']

# for col in cat_cols:
#     path = os.path.join(AGENT1_DIR, f'label_encoder_{col}.pkl')
#     if os.path.exists(path):
#         label_encoders[col] = joblib.load(path)

# # === Agent 2 Paths ===
# AGENT2_DIR = './models/agent2_xgboost'
# xgb_model = joblib.load(os.path.join(AGENT2_DIR, 'xgb_model.pkl'))

# # === Step 1: Get anomaly score from Agent 1 ===
# def agent1_get_anomaly_score(input_json):
#     df = pd.DataFrame([input_json])

#     # Date
#     df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
#     df['day'] = df['Date'].dt.day
#     df['month'] = df['Date'].dt.month
#     df['year'] = df['Date'].dt.year
#     df.drop(columns=['Date'], inplace=True)

#     # Time
#     df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S', errors='coerce')
#     df['hour'] = df['Time'].dt.hour
#     df['minute'] = df['Time'].dt.minute
#     df['second'] = df['Time'].dt.second
#     df.drop(columns=['Time'], inplace=True)

#     # Hash sender/receiver account
#     for col in ['Sender_account', 'Receiver_account']:
#         if col in df.columns:
#             df[col + '_hash'] = df[col].astype(str).apply(lambda x: hash(x) % 1000)
#             df.drop(columns=col, inplace=True)

#     # Apply label encoding
#     for col in cat_cols:
#         if col in df.columns:
#             le = label_encoders.get(col)
#             if le:
#                 try:
#                     df[col] = le.transform([str(df[col].values[0])])[0]
#                 except:
#                     df[col] = 0  # fallback for unseen value
#             else:
#                 df[col] = 0

#     df.fillna(0, inplace=True)
#     X_input = df.values
#     X_scaled = scaler_ae.transform(X_input)

#     # Predict reconstruction error
#     X_pred = autoencoder.predict(X_scaled, verbose=0)
#     recon_error = np.mean(np.square(X_scaled - X_pred), axis=1)
#     denom = recon_error.max() - recon_error.min()
#     if denom == 0:
#         anomaly_score = np.zeros_like(recon_error)
#     else:
#         anomaly_score = (recon_error - recon_error.min()) / denom

#     return anomaly_score[0]

# # === Step 2: Full pipeline ===
# def predict_fraud(input_json):
#     anomaly_score = agent1_get_anomaly_score(input_json)

#     # Preprocess for XGBoost (Agent 2)
#     X_final = preprocess_for_agent2(input_json, [anomaly_score])
#     y_proba = xgb_model.predict_proba(X_final)[0][1]
#     y_pred = int(y_proba > 0.5)

#     return {
#     "prediction": int(y_pred),
#     "fraud_probability": float(round(y_proba, 4)),
#     # "anomaly_score": float(round(anomaly_score, 4))
# }


# # === Run on sample input ===
# if __name__ == "__main__":
#     test_input = {
#         "Sender_account": "ACC1234",
#         "Receiver_account": "ACC5678",
#         "Sender_bank_location": "Mumbai",
#         "Receiver_bank_location": "Delhi",
#         "Payment_type": "Wire Transfer",
#         "Laundering_type": "Smurfing",
#         "Payment_currency": "INR",
#         "Received_currency": "INR",
#         "Amount": 45000,
#         "Date": "2025-07-13",
#         "Time": "12:30:45"
#     }

#     output = predict_fraud(test_input)
#     print(json.dumps(output, indent=2))
import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf

# === Add root for shared import ===
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

from agents.shared_preprocessing import preprocess_for_agent2, preprocess_for_lstm
from agents.lstm_sequence_buffer import update_sequence_buffer_and_predict

# === Agent 1: AutoEncoder ===
AGENT1_DIR = './models/agent1_autoencoder'
autoencoder = tf.keras.models.load_model(os.path.join(AGENT1_DIR, 'autoencoder_model.keras'))
scaler_ae = joblib.load(os.path.join(AGENT1_DIR, 'scaler.pkl'))

label_encoders = {}
cat_cols = ['Payment_currency', 'Received_currency', 'Sender_bank_location',
            'Receiver_bank_location', 'Payment_type']

for col in cat_cols:
    path = os.path.join(AGENT1_DIR, f'label_encoder_{col}.pkl')
    if os.path.exists(path):
        label_encoders[col] = joblib.load(path)

# === Agent 2: XGBoost ===
AGENT2_DIR = './models/agent2_xgboost'
xgb_model = joblib.load(os.path.join(AGENT2_DIR, 'xgb_model.pkl'))

# === Agent 3: LSTM ===
AGENT3_DIR = './models/agent3_lstm'
lstm_model = tf.keras.models.load_model(os.path.join(AGENT3_DIR, 'lstm_model.keras'))
lstm_scaler = joblib.load(os.path.join(AGENT3_DIR, 'scaler.pkl'))

# === Agent 1: Anomaly Score ===
def agent1_get_anomaly_score(input_json):
    df = pd.DataFrame([input_json])

    # Date & Time
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['day'] = df['Date'].dt.day
    df['month'] = df['Date'].dt.month
    df['year'] = df['Date'].dt.year
    df.drop(columns=['Date'], inplace=True)

    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S', errors='coerce')
    df['hour'] = df['Time'].dt.hour
    df['minute'] = df['Time'].dt.minute
    df['second'] = df['Time'].dt.second
    df.drop(columns=['Time'], inplace=True)

    # Hash account IDs
    for col in ['Sender_account', 'Receiver_account']:
        df[col + '_hash'] = df[col].astype(str).apply(lambda x: hash(x) % 1000)
        df.drop(columns=col, inplace=True)

    # Encode categories
    for col in cat_cols:
        if col in df.columns:
            le = label_encoders.get(col)
            if le:
                try:
                    df[col] = le.transform([str(df[col].values[0])])[0]
                except:
                    df[col] = 0
            else:
                df[col] = 0

    df.fillna(0, inplace=True)
    X_input = df.values
    X_scaled = scaler_ae.transform(X_input)

    # Predict
    X_pred = autoencoder.predict(X_scaled, verbose=0)
    recon_error = np.mean(np.square(X_scaled - X_pred), axis=1)
    denom = recon_error.max() - recon_error.min()
    if denom == 0:
        anomaly_score = np.zeros_like(recon_error)
    else:
        anomaly_score = (recon_error - recon_error.min()) / denom

    return anomaly_score[0]

# === Main Pipeline ===
def predict_fraud(input_json):
    # Agent 1
    anomaly_score = agent1_get_anomaly_score(input_json)

    # Agent 2
    X_final = preprocess_for_agent2(input_json, [anomaly_score])
    y_proba = xgb_model.predict_proba(X_final)[0][1]
    # y_pred = int(y_proba > 0.5)

    # Agent 3
    lstm_input = preprocess_for_lstm(input_json, anomaly_score, y_proba, lstm_scaler)
    sender_id = hash(input_json['Sender_account']) % 1000
    lstm_fraud_prob = update_sequence_buffer_and_predict(sender_id, lstm_input, lstm_model)

    return {
    # "prediction": int(y_pred),
    "fraud_probability": float(round(y_proba, 4)),
    # "anomaly_score": float(round(anomaly_score, 4)),
    "lstm_fraud_probability": float(round(lstm_fraud_prob, 4))
}


# === Test Run ===
if __name__ == "__main__":
    test_input = {
        "Sender_account": "2365007895",
        "Receiver_account": "ACC5678",
        "Sender_bank_location": "Mumbai",
        "Receiver_bank_location": "Delhi",
        "Payment_type": "Wire Transfer",
        # "Laundering_type": "Smurfing",
        "Payment_currency": "INR",
        "Received_currency": "INR",
        "Amount": 800000,
        "Date": "2025-07-13",
        "Time": "12:30:45"
    }

    output = predict_fraud(test_input)
    print(json.dumps(output, indent=2))
