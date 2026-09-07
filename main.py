import os
import requests
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input

def fetch_and_process_daily_data():
    """
    Pulls the latest daily retail scan dataset dynamically.
     Expects a live endpoint or daily automated data feed containing columns like:
    ['Date', 'Region', 'Brand', 'Flavor', 'Units_Sold']
    """
    live_data_url = os.getenv("DAILY_RETAIL_DATA_URL")
    
    if live_data_url:
        # Pulls yesterday's updated data stream directly from live feed
        df = pd.read_csv(live_data_url)
    else:
        # Fallback to an ingestion step simulating daily live data parsing
        # (In production, your GitHub Action downloads yesterday's fresh feed from your data pipeline source)
        df = pd.read_csv("latest_daily_scanner_feed.csv")

    # Ensure date-time sorting to isolate yesterday's specific data window
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')

    # Dynamically extract unique brands and flavors present in the data itself—zero hardcoding.
    unique_brands = df['Brand'].unique().tolist()
    unique_flavors = df['Flavor'].unique().tolist()
    
    print(f"Dynamically Discovered Brands: {unique_brands}")
    print(f"Dynamically Discovered Flavors: {unique_flavors}")

    # Pivot dynamically using whatever brands and flavors are found in the raw data feed
    pivot_df = df.pivot_table(index='Date', columns=['Region', 'Brand', 'Flavor'], values='Units_Sold', fill_value=0)
    
    dataset_values = pivot_df.values.astype(np.float32)
    max_val = np.max(dataset_values) if np.max(dataset_values) > 0 else 1.0
    normalized_data = dataset_values / max_val
    
    return pivot_df, normalized_data

def run_tensorflow_lstm_forecast(pivot_df, normalized_data):
    """
    Feeds dynamic historical tensor sequences through an LSTM network 
    to project tomorrow's leading product velocity across the freezer aisle.
    """
    window_size = 7
    if len(normalized_data) <= window_size:
        return pivot_df.columns[0][1], pivot_df.columns[0][2], pivot_df.columns[0][0]

    X, y = [], []
    for i in range(len(normalized_data) - window_size):
        X.append(normalized_data[i:i + window_size])
        y.append(normalized_data[i + window_size])
        
    X = np.array(X)
    y = np.array(y)

    # TensorFlow LSTM Architecture for time-series momentum
    model = Sequential([
        Input(shape=(X.shape[1], X.shape[2])),
        LSTM(32, activation='relu'),
        Dense(X.shape[2], activation='linear')
    ])
    
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=5, verbose=0)
    
    # Predict next interval trends based on the latest window
    last_window = np.array([normalized_data[-window_size:]])
    predicted_vector = model.predict(last_window, verbose=0)[0]
    
    # Map the highest tensor index back to its respective Region, Brand, and Flavor dynamically
    max_index = np.argmax(predicted_vector)
    top_region, top_brand, top_flavor = pivot_df.columns[max_index]
    
    return top_brand, top_flavor, top_region

def generate_post_content(brand, flavor, region):
    message = (
        f"🍦 The Daily Scoop: Autonomous Freezer Aisle Intelligence 🐾\n\n"
        f"Dynamic TensorFlow LSTM Forecast (Previous Day Ingest):\n"
        f"🏢 Market Brand: *{brand}*\n"
        f"🎯 Leading Flavor: *{flavor}*\n"
        f"🗺️ High-Velocity Region: *{region}*\n\n"
        f"By dynamically parsing yesterday's multi-brand scanner feeds and running them through a neural network time-series pipeline, "
        f"we isolate nationwide demand shifts as they happen. Petey and Andrew are auditing the entire freezer aisle data stream!\n\n"
        f"#SNOOPISHIRING #DrBombay #IceCreamTrends #DataScience #TensorFlow #RetailAnalytics"
    )
    return message

def post_to_facebook(message):
    page_access_token = os.getenv("FB_PAGE_ACCESS_TOKEN")
    page_id = os.getenv("FB_PAGE_ID")
    
    if not page_access_token or not page_id:
        print("API credentials missing. Dynamic Pipeline Preview:\n")
        print(message)
        return

    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
    payload = {"message": message, "access_token": page_access_token}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Successfully posted dynamic market insights to Facebook!")
    else:
        print(f"Error posting: {response.json()}")

if __name__ == "__main__":
    pivot_df, normalized_data = fetch_and_process_daily_data()
    top_brand, top_flavor, top_region = run_tensorflow_lstm_forecast(pivot_df, normalized_data)
    post_text = generate_post_content(top_brand, top_flavor, top_region)
    post_to_facebook(post_text)
