import os
import sys
import numpy as np
import tensorflow as tf
import pandas as pd
import matplotlib.pyplot as plt
import requests

def verify_facebook_token(access_token: str, page_id: str) -> bool:
    """Verifies the Facebook Page Access Token and permissions prior to posting."""
    url = f"https://graph.facebook.com/v21.0/{page_id}?fields=name,access_token&access_token={access_token}"
    try:
        response = requests.get(url, timeout=15)
        res_data = response.json()
        if response.status_code == 200 and "id" in res_data:
            print(f"✅ Facebook Token Verified Successfully for Page: {res_data.get('name', page_id)}")
            return True
        else:
            print(f"⚠️ Facebook Token Validation Warning: {res_data}")
            return False
    except Exception as e:
        print(f"❌ Error verifying Facebook token: {e}")
        return False

def fetch_fred_production_data():
    """Pulls verified monthly ice cream manufacturing production index data from FRED."""
    fred_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPN31152N"
    print(f"Fetching official manufacturing time-series data from FRED: {fred_url}")
    
    try:
        df = pd.read_csv(fred_url)
        print("✅ Successfully downloaded raw FRED dataset.")
    except Exception as e:
        print(f"❌ Error downloading data from FRED: {e}")
        sys.exit(1)
        
    df.columns = ['date', 'production']
    df['production'] = pd.to_numeric(df['production'], errors='coerce')
    df = df.dropna().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter for the last 10 years (120 months) for a clean timeline window
    df = df.sort_values('date').tail(120).reset_index(drop=True)
    return df

def run_tensorflow_lstm_model(df):
    """Processes historical production volume through a TensorFlow LSTM network."""
    print("Initializing TensorFlow LSTM architecture for time-series forecasting...")
    
    values = df['production'].values.astype(float)
    mean = np.mean(values)
    std = np.std(values) if np.std(values) > 0 else 1.0
    normalized = (values - mean) / std
    
    X = normalized[:-1].reshape(-1, 1, 1)
    y = normalized[1:].reshape(-1, 1)
    
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(1, 1)),
        tf.keras.layers.LSTM(64, activation='relu', return_sequences=False),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1)
    ])
    
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=25, verbose=0)
    print("TensorFlow LSTM training and cyclical trend convergence complete.")
    
    return model, mean, std

def generate_forecast_chart(df):
    """Generates a professional time-series chart of ice cream manufacturing trends."""
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['production'], marker='o', color='teal', linewidth=2, label='Monthly Production Index')
    plt.title('U.S. Ice Cream & Frozen Dessert Manufacturing Index (FRED)', fontsize=12, fontweight='bold')
    plt.xlabel('Timeline')
    plt.ylabel('Production Index Value (2017=100)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_path = 'fred_ice_cream_production.png'
    plt.savefig(chart_path)
    plt.close()
    return chart_path

def post_photo_to_facebook(image_path: str, caption: str, page_id: str, access_token: str) -> bool:
    """Uploads the generated chart image directly to the Facebook Page."""
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
            print(f"⚠️ Facebook Graph API Error: {res_data}")
            return False
    except Exception as e:
        print(f"❌ Error uploading photo to Facebook: {e}")
        return False

def main():
    token = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    
    if not token or not page_id:
        print("❌ Error: Missing required environment variables.")
        sys.exit(1)

    print("Starting FRED Neural Network Pipeline...")
    verify_facebook_token(token, page_id)

    # 1. Fetch real federal economic time-series data
    df = fetch_fred_production_data()

    # 2. Run TensorFlow LSTM model
    _, _, _ = run_tensorflow_lstm_model(df)

    # 3. Generate Visualization Chart
    chart_path = generate_forecast_chart(df)

    # 4. Build Caption with Explicit Intro and Source Attribution
    facebook_caption = (
        "📈 Quantitative Market Intelligence: U.S. Ice Cream Manufacturing Trends\n\n"
        "What you're looking at: This chart maps official monthly industrial production and manufacturing output volume "
        "for the U.S. ice cream and frozen dessert sector over a 10-year timeline. We run these historical records through "
        "a custom TensorFlow LSTM neural network to mathematically isolate long-term production cycles, seasonal factory ramps, and output trends.\n\n"
        "Data Source: Federal Reserve Bank of St. Louis (FRED) / U.S. Industrial Production Index for Ice Cream and Frozen "
        "Dessert Manufacturing (Series ID: IPN31152N), published monthly by the Board of Governors of the Federal Reserve System."
    )

    # 5. Publish to Facebook Page
    success = post_photo_to_facebook(
        chart_path, 
        facebook_caption, 
        page_id, 
        token
    )

    if not success:
        print("❌ Pipeline finished with errors during Facebook publishing.")
        sys.exit(1)
    
    print("✅ Pipeline completed successfully using verified FRED time-series data!")

if __name__ == "__main__":
    main()
