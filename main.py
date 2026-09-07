import os
import requests
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
from google import genai

def fetch_and_process_market_data():
    """
    Pulls yesterday's raw nationwide freezer aisle scanner feed dynamically.
    Expects columns: ['Date', 'Region', 'Brand', 'Flavor', 'Units_Sold']
    Zero hardcoded brands or flavors—everything is extracted dynamically from the data stream.
    """
    data_url = os.getenv("DAILY_RETAIL_DATA_URL")
    
    if data_url:
        df = pd.read_csv(data_url)
    else:
        raise ValueError(
            "DAILY_RETAIL_DATA_URL environment variable is missing or no live data file is provided. "
            "The script requires a raw incoming dataset to dynamically extract brands and flavors."
        )

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Dynamically compute and extract the top 20 brands and top 20 flavors entirely from incoming data volume
    top_20_brands = df.groupby('Brand')['Units_Sold'].sum().nlargest(20).index.tolist()
    top_20_flavors = df.groupby('Flavor')['Units_Sold'].sum().nlargest(20).index.tolist()
    
    print(f"Dynamically Extracted Top 20 Brands: {top_20_brands}")
    print(f"Dynamically Extracted Top 20 Flavors: {top_20_flavors}")
    
    # Filter dataset to focus our time-series tensor matrix on the top 20 market leaders discovered above
    df_filtered = df[df['Brand'].isin(top_20_brands) & df['Flavor'].isin(top_20_flavors)]

    # Pivot dynamically for TensorFlow LSTM ingestion
    pivot_df = df_filtered.pivot_table(index='Date', columns=['Region', 'Brand', 'Flavor'], values='Units_Sold', fill_value=0)
    dataset_values = pivot_df.values.astype(np.float32)
    normalized_data = dataset_values / (np.max(dataset_values) if np.max(dataset_values) > 0 else 1.0)
    
    return pivot_df, normalized_data, top_20_brands

def run_tensorflow_lstm_analysis(pivot_df, normalized_data):
    """
    Feeds the dynamic tensor sequences through an LSTM network 
    to forecast tomorrow's highest-velocity product across the competitive landscape.
    """
    window_size = 7
    if len(normalized_data) <= window_size:
        return pivot_df.columns[0][1], pivot_df.columns[0][2], pivot_df.columns[0][0], 1.0

    X, y = [], []
    for i in range(len(normalized_data) - window_size):
        X.append(normalized_data[i:i + window_size])
        y.append(normalized_data[i + window_size])
        
    X, y = np.array(X), np.array(y)

    model = Sequential([
        Input(shape=(X.shape[1], X.shape[2])),
        LSTM(32, activation='relu'),
        Dense(X.shape[2], activation='linear')
    ])
    
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=5, verbose=0)
    
    last_window = np.array([normalized_data[-window_size:]])
    predicted_vector = model.predict(last_window, verbose=0)[0]
    
    max_index = np.argmax(predicted_vector)
    top_region, top_brand, top_flavor = pivot_df.columns[max_index]
    predicted_score = float(predicted_vector[max_index])
    
    return top_brand, top_flavor, top_region, predicted_score

def generate_ai_caption(brand, flavor, region, score):
    """
    Uses the Google AI SDK to write a fresh market intelligence report 
    based on the model's output.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return f"🍦 The Daily Scoop\n\nTop Market Leader: {brand} - {flavor} in the {region} (Score: {score:.2f}).\n\n#SNOOPISHIRING #DrBombay"

    client = genai.Client(api_key=api_key)
    prompt = (
        f"You are an expert data scientist and gourmet ice cream taste tester running 'The Daily Scoop'. "
        f"Our TensorFlow LSTM model dynamically parsed nationwide retail scan data, extracted the top-performing brands and flavors, "
        f"and identified that Brand: {brand}, Flavor: {flavor}, is surging in the {region} region with a projected velocity score of {score:.2f}. "
        f"Write a fresh, highly engaging social media post highlighting this data-driven market trend. "
        f"Blend machine learning time-series insights with gourmet dessert analysis, and include hashtags like #SNOOPISHIRING #DrBombay #IceCreamTrends #DataScience."
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def post_to_facebook(message):
    page_access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    if not page_access_token or not page_id:
        print("--- PREVIEW MODE (Credentials Not Found) ---\n")
        print(message)
        return

    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
    payload = {"message": message, "access_token": page_access_token}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Successfully published dynamic market report to Facebook!")
    else:
        print(f"Error publishing: {response.json()}")

if __name__ == "__main__":
    pivot_df, normalized_data, top_brands = fetch_and_process_market_data()
    brand, flavor, region, score = run_tensorflow_lstm_analysis(pivot_df, normalized_data)
    ai_post = generate_ai_caption(brand, flavor, region, score)
    post_to_facebook(ai_post)
