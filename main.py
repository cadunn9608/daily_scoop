import os
import requests
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
from google import genai

def generate_live_market_stream_with_fallback(client):
    """
    Generates runtime market data including regions, store chains, brands, 
    and flavors using a prioritized model fallback chain.
    """
    candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"]
    prompt = (
        "Generate a realistic JSON dataset representing yesterday's nationwide ice cream retail scan data across US regions (Northeast, Midwest, South, West) "
        "and major grocery store chains/retailers (e.g., Kroger, Whole Foods, Safeway, Target, Publix, Albertsons). "
        "Include multiple competing brands and flavors organically, ensuring brands like Dr. Bombay and other top market competitors are present. "
        "The output must be a valid JSON array of objects with these exact keys: "
        "'Date' (string YYYY-MM-DD), 'Region' (string), 'Store' (string), 'Brand' (string), 'Flavor' (string), 'Units_Sold' (integer). "
        "Provide at least 150 rows of data. Return ONLY valid JSON."
    )

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()

            data = json.loads(raw_text)
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Model {model_name} failed for data generation: {e}. Falling back to next available model...")
            continue

    raise RuntimeError("All model fallback tiers failed to generate market data stream.")

def process_and_analyze_with_tensorflow(df):
    """
    Dynamically extracts top brands and flavors, constructs an in-memory 
    tensor matrix including Region and Store dimensions, and runs LSTM forecasting.
    """
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    top_brands = df.groupby('Brand')['Units_Sold'].sum().nlargest(20).index.tolist()
    top_flavors = df.groupby('Flavor')['Units_Sold'].sum().nlargest(20).index.tolist()
    
    df_filtered = df[df['Brand'].isin(top_brands) & df['Flavor'].isin(top_flavors)]
    
    # Pivot matrix now includes Region, Store, Brand, and Flavor dimensions
    pivot_df = df_filtered.pivot_table(index='Date', columns=['Region', 'Store', 'Brand', 'Flavor'], values='Units_Sold', fill_value=0)
    dataset_values = pivot_df.values.astype(np.float32)
    
    if len(dataset_values) <= 7:
        col = pivot_df.columns[0]
        return col[0], col[1], col[2], col[3], 1.0

    normalized_data = dataset_values / np.max(dataset_values)
    
    window_size = 7
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
    top_region, top_store, top_brand, top_flavor = pivot_df.columns[max_index]
    predicted_score = float(predicted_vector[max_index])
    
    return top_brand, top_flavor, top_region, top_store, predicted_score

def generate_ai_report_with_fallback(client, brand, flavor, region, store, score):
    """
    Uses a robust multi-model fallback chain to generate the daily caption text,
    incorporating store-level retail insights.
    """
    candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"]
    prompt = (
        f"You are an expert data scientist and gourmet ice cream taste tester running 'The Daily Scoop'. "
        f"Our TensorFlow LSTM model analyzed today's runtime market stream and found that Brand: {brand}, "
        f"Flavor: {flavor}, is surging at *{store}* in the {region} region with a velocity score of {score:.2f}. "
        f"Write a sharp, engaging social media post highlighting this store-level data-driven trend, including #SNOOPISHIRING #DrBombay #DataScience."
    )

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"Model {model_name} failed for caption generation: {e}. Trying next fallback tier...")
            continue

    return f"🍦 The Daily Scoop\n\nTop Market Leader: {brand} - {flavor} at {store} ({region}) [Score: {score:.2f}].\n\n#SNOOPISHIRING #DrBombay #DataScience"

def post_to_facebook(message):
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    if not token or not page_id:
        print("--- PREVIEW MODE (No FB Credentials) ---\n")
        print(message)
        return

    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
    response = requests.post(url, data={"message": message, "access_token": token})
    if response.status_code == 200:
        print("Successfully published to Facebook!")
    else:
        print(f"Error: {response.json()}")

if __name__ == "__main__":
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required.")

    client = genai.Client(api_key=api_key)
    
    market_df = generate_live_market_stream_with_fallback(client)
    brand, flavor, region, store, score = process_and_analyze_with_tensorflow(market_df)
    social_post = generate_ai_report_with_fallback(client, brand, flavor, region, store, score)
    post_to_facebook(social_post)
