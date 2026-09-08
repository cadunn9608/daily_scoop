import os
import sys
import requests
from requests.exceptions import RequestException, Timeout
from google import genai

# Initialize environment variables
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def run_lstm_forecasting():
    """Runs the LSTM market trend forecasting model."""
    print("Starting Daily Scoop Market Intelligence Pipeline...")
    
    # Placeholder/Execution logic for LSTM model score calculation
    # In your pipeline, this evaluates market data and produces an index score
    index_score = -0.0319
    
    print(f"LSTM Trend Forecasting complete. Index score: {index_score:.4f}")
    return index_score

def generate_post_content(index_score: float) -> str:
    """Generates social media content using Google GenAI (Gemini)."""
    target_model = "gemini-3.7-flash"
    print(f"Attempting generation with {target_model}...")
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = (
        f"Write an engaging, fun, artisanal ice cream market update post for Facebook "
        f"for 'The Daily Scoop with Sniff and Paws'. The weekly market momentum index score is {index_score}. "
        f"Include wild flavor ideas, regional hotspots, and a call-to-action question. Format with emojis and hashtags."
    )

    response = client.models.generate_content(
        model=target_model,
        contents=prompt,
    )
    
    content = response.text
    print("Generated Post Content:\n" + content)
    return content

def post_to_facebook(message: str, page_id: str, access_token: str) -> bool:
    """Publishes content to a Facebook Page with robust error checking and diagnostics."""
    url = f"https://graph.facebook.com/v21.0/{page_id}/feed"
    payload = {
        "message": message,
        "access_token": access_token
    }
    
    try:
        response = requests.post(url, data=payload, timeout=15)
        response_data = response.json()
        
        # Check for successful publication
        if response.status_code == 200 and "id" in response_data:
            print(f"Successfully posted to Facebook! Post ID: {response_data['id']}")
            return True
            
        # Handle structured Meta API errors gracefully
        error_info = response_data.get("error", {})
        error_code = error_info.get("code")
        error_message = error_info.get("message", "Unknown Graph API error")
        
        print(f"⚠️ Facebook API Error (HTTP {response.status_code} | Code {error_code}):")
        print(f"   -> Message: {error_message}")
        
        # Targeted diagnostics for common configuration errors
        if error_code == 200:
            print("   -> Diagnosis: Typically caused by using a User-scoped token instead of a Page-scoped token,")
            print("      or missing 'pages_read_engagement' / 'pages_manage_posts' permissions in Meta App Use Cases.")
        elif error_code == 283:
            print("   -> Diagnosis: The token lacks the required 'pages_read_engagement' permission scope.")
        elif error_code == 190:
            print("   -> Diagnosis: The access token has expired or been invalidated. Please regenerate it.")
            
        return False

    except Timeout:
        print("❌ Error: Connection to the Facebook Graph API timed out after 15 seconds.")
        return False
    except RequestException as e:
        print(f"❌ Error: A network or HTTP exception occurred while reaching Facebook: {e}")
        return False

def main():
    # Verify required secrets are present
    if not FACEBOOK_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        print("❌ Error: FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID is missing from environment variables.")
        sys.exit(1)

    # Step 1: Run LSTM Trend Forecasting
    index_score = run_lstm_forecasting()

    # Step 2: Generate Post Content via Gemini
    try:
        post_content = generate_post_content(index_score)
    except Exception as e:
        print(f"❌ Error generating content with Gemini: {e}")
        sys.exit(1)

    # Step 3: Publish to Facebook Page with robust error checking
    success = post_to_facebook(post_content, FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN)
    
    if not success:
        print("❌ Pipeline finished with errors during Facebook publication.")
        sys.exit(1)
    
    print("✅ Pipeline completed successfully!")

if __name__ == "__main__":
    main()
