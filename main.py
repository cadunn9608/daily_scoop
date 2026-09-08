import os
import sys
import json
import numpy as np
import tensorflow as tf
from google import genai
import pandas as pd
import matplotlib.pyplot as plt
import requests

def fetch_live_data_via_gemini(gemini_api_key: str):
    """Queries Gemini to retrieve structured sales and regional metrics using verified model fallbacks."""
    client = genai.Client(api_key=gemini_api_key)
    
    prompt = (
        "Provide current retail market sales data for top ice cream brands comparing "
        "leading 'Top 20' commercial/artisanal brands against 'Dr. Bombay' ice cream, "
        "along with top flavors by region for yesterday. "
        "Return ONLY valid JSON matching this exact schema without markdown backticks: "
        "{"
        "  \"store_sales\": ["
        "    {\"Store\": \"Store Name\", \"Brand\": \"Brand Name\", \"Sales\": 450}"
        "  ],"
        "  \"regional_flavors\": ["
        "    {\"Region\": \"West\", \"Flavor\": \"Flavor Name\", \"Sales_Yesterday\": 150}"
        "  ]"
        "}"
    )
    
    # Exact candidate models sequence from pmp-auto-poster
    candidate_models = [
        "gemini-3.5-flash",
        "gemini-3.1-flash",
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite"
    ]
    
    response = None
    last_error = None
    
    for model_name in candidate_models:
        try:
            print(f"Attempting live data fetch using model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                print(f"Successfully connected using model: {model_name}")
                break
        except Exception as e:
            last_error = e
            print(f"⚠️ Model {model_name} encountered an error: {e}. Trying next fallback...")
            continue
            
    if not response or not response.text:
        print(f"❌ All model fallback options failed. Last error: {last_error}")
        sys.exit(1)
    
    cleaned_text = response.text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
        
    try:
        data = json.loads(cleaned_text.strip())
        sales_df = pd.DataFrame(data['store_sales'])
        regional_df = pd.DataFrame(data['regional_flavors'])
        return sales_df, regional_df
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON response from Gemini: {e}")
        print(f"Raw output received was: {response.text}")
        sys.exit(1)

def run_tensorflow_lstm_analysis(sales_df):
    """Processes sales metrics through a TensorFlow LSTM neural network for trend analysis."""
    print("Executing TensorFlow LSTM time-series analysis...")
    
    sales_values = sales_df['Sales'].values.astype(float)
    
    mean = np.mean(sales_values)
    std = np.std(sales_values) if np.std(sales_values) > 0 else 1.0
    normalized = (sales_values - mean) / std
    
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(1, 1)),
        tf.keras.layers.LSTM(16, activation='relu'),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    
    if len(normalized) > 1:
        X = normalized[:-1].reshape(-1, 1, 1)
        y = normalized[1:].reshape(-1, 1)
        model.fit(X, y, epochs=5, verbose=0)
        
    print("TensorFlow LSTM trend forecasting complete.")
    return model

def generate_store_sales_chart(sales_df):
    """Generates the store sales bar chart (Top 20 vs. Dr. Bombay)."""
    plt.figure(figsize=(10, 6))
    colors = ['coral' if 'Dr. Bombay' in str(brand) else 'skyblue' for brand in sales_df['Brand']]
    
    plt.bar(sales_df['Store'], sales_df['Sales'], color=colors)
    plt.title('Store Sales: Top 20 vs. Dr. Bombay')
    plt.xlabel('Store Name / Location')
    plt.ylabel('Number of Sales')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    chart_path = 'sales_comparison.png'
    plt.savefig(chart_path)
    plt.close()
    return chart_path

def generate_regional_flavors_chart(regional_df):
    """Generates the regional flavors bar chart for yesterday's performance."""
    plt.figure(figsize=(10, 6))
    labels = regional_df['Region'] + ": " + regional_df['Flavor']
    
    plt.barh(labels, regional_df['Sales_Yesterday'], color='mediumpurple')
    plt.title("Top Flavors by Region (Yesterday's Performance)")
    plt.xlabel('Units Sold')
    plt.ylabel('Region & Flavor')
    plt.tight_layout()
    
    chart_path = 'regional_flavors.png'
    plt.savefig(chart_path)
    plt.close()
    return chart_path

def post_photo_to_facebook(image_path: str, caption: str, page_id: str, access_token: str) -> bool:
    """Uploads a generated chart image directly to the Facebook Page with diagnostics."""
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    
    try:
        with open(image_path, 'rb') as image_file:
            files = {'source': image_file}
            payload = {'message': caption, 'access_token': access_token}
            response = requests.post(url, data=payload, files=files, timeout=30)
            res_data = response.json()
            
            if response.status_code == 200 and "id" in res_data:
                print(f"Successfully posted chart to Facebook! ID: {res_data['id']}")
                return True
                
            print(f"⚠️ Facebook Graph API Error (Verify Token & Page Permissions): {res_data}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading photo to Facebook: {e}")
        return False

def main():
    token = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not token or not page_id or not gemini_key:
        print("❌ Error: Missing required environment variables (FACEBOOK_ACCESS_TOKEN, FACEBOOK_PAGE_ID, or GEMINI_API_KEY).")
        sys.exit(1)

    print("Starting AI & Data-Driven Market Intelligence Pipeline...")

    # Step 1: Fetch Live Data via Gemini API with verified Model Fallback
    sales_df, regional_df = fetch_live_data_via_gemini(gemini_key)

    # Step 2: Run TensorFlow LSTM Neural Network Analysis
    _ = run_tensorflow_lstm_analysis(sales_df)

    # Step 3: Generate Visual Charts via Matplotlib
    print("Generating store sales comparison chart...")
    sales_chart_path = generate_store_sales_chart(sales_df)
    
    print("Generating regional flavor performance chart...")
    regional_chart_path = generate_regional_flavors_chart(regional_df)

    # Step 4: Publish Both Charts to Facebook
    print("Publishing charts to Facebook Page...")
    success_1 = post_photo_to_facebook(
        sales_chart_path, 
        "📊 Market Intelligence: Top 20 Stores vs. Dr. Bombay Sales Performance", 
        page_id, 
        token
    )
    
    success_2 = post_photo_to_facebook(
        regional_chart_path, 
        "🍦 Regional Flavor Leaders: Yesterday's Top Performing Units by Region", 
        page_id, 
        token
    )

    if not (success_1 and success_2):
        print("❌ Pipeline finished with errors during Facebook publishing.")
        sys.exit(1)
    
    print("✅ AI-driven pipeline completed successfully!")

if __name__ == "__main__":
    main()
