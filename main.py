import os
import sys
import numpy as np
import tensorflow as tf
from google import genai
from google.genai import errors
import requests

# 1. Environment & Credential Validation
FB_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([FB_ACCESS_TOKEN, FB_PAGE_ID, GEMINI_API_KEY]):
    print("Error: Missing required environment variables/secrets.", file=sys.stderr)
    sys.exit(1)

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Define Model Fallback Hierarchy
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro"
]

def generate_with_fallback(prompt: str) -> str:
    """Iterates through model tiers to guarantee generation resilience."""
    for model_name in GEMINI_MODELS:
        try:
            print(f"Attempting generation with {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
        except errors.APIError as e:
            print(f"Model {model_name} failed with API error: {e}. Trying next fallback...")
        except Exception as e:
            print(f"Unexpected error with {model_name}: {e}. Trying next fallback...")
    
    raise RuntimeError("All Gemini model fallback tiers failed to generate content.")

def run_in_memory_lstm_forecast() -> float:
    """Executes a strictly in-memory TensorFlow LSTM trend prediction."""
    # Synthetic / In-Memory Market Trend Time-Series Data Simulation
    data = np.sin(np.linspace(0, 50, 100)) + np.random.normal(0, 0.1, 100)
    
    X = []
    y = []
    window_size = 10
    for i in range(len(data) - window_size):
        X.append(data[i:i+window_size])
        y.append(data[i+window_size])
        
    X = np.array(X)[..., np.newaxis]
    y = np.array(y)
    
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(32, input_shape=(window_size, 1)),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=5, verbose=0)
    
    # Predict next trend index
    latest_window = data[-window_size:][np.newaxis, ..., np.newaxis]
    prediction = model.predict(latest_window, verbose=0)
    return float(prediction[0][0])

def post_to_facebook(message: str):
    """Publishes the generated intelligence payload to the Facebook Page via Graph API."""
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": FB_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Successfully posted to Facebook!")
    else:
        print(f"Failed to post to Facebook: {response.text}", file=sys.stderr)
        sys.exit(1)

def main():
    print("Starting Daily Scoop Market Intelligence Pipeline...")
    
    # 1. Run LSTM Forecast in memory
    trend_score = run_in_memory_lstm_forecast()
    print(f"LSTM Trend Forecasting complete. Index score: {trend_score:.4f}")
    
    # 2. Generate Content via Gemini with Fallbacks
    prompt = (
        f"Generate a fun, engaging social media post for 'The Daily Scoop with Sniff and Paws' "
        f"highlighting current artisanal ice cream market trends, unique flavor profiles, and regional hotspots. "
        f"Current market momentum index is {trend_score:.4f}. Keep it snappy and reader-friendly."
    )
    
    post_content = generate_with_fallback(prompt)
    print("Generated Post Content:\n", post_content)
    
    # 3. Publish to Facebook Page
    post_to_facebook(post_content)

if __name__ == "__main__":
    main()
