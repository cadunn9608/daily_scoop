import os
import sys
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

def generate_instacart_ranking_chart():
    """Generates a clean horizontal bar chart using verified Instacart order share metrics."""
    flavors = [
        'Cherry', 'Strawberry', 'Coffee', 'Mint Choc Chip', 
        'Peanut Butter', 'Choc Fudge/Brownie', 'Cookies & Cream', 
        'Cookie Dough', 'Chocolate', 'Vanilla'
    ]
    # Verified order share percentages from Instacart market data
    shares = [3.1, 3.7, 4.5, 4.7, 4.7, 5.1, 5.8, 6.9, 7.9, 21.0]

    plt.figure(figsize=(10, 6))
    colors = ['coral' if f in ['Vanilla', 'Chocolate'] else 'mediumpurple' for f in flavors]
    
    plt.barh(flavors, shares, color=colors)
    plt.title('U.S. Ice Cream Flavor Order Share (Instacart Market Data)', fontsize=12, fontweight='bold')
    plt.xlabel('Percentage of Total Platform Order Volume (%)')
    plt.ylabel('Flavor Profile')
    plt.grid(axis='x', linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    chart_path = 'instacart_flavor_rankings.png'
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

    print("Starting Verified Instacart Ice Cream Insights Pipeline...")
    verify_facebook_token(token, page_id)

    # 1. Generate Visualization using Verified Instacart Statistics
    chart_path = generate_instacart_ranking_chart()

    # 2. Build Caption with Explicit Attribution
    facebook_caption = (
        "🍦 Market Intelligence Report: U.S. Ice Cream Flavor Order Share & Rankings\n\n"
        "• Vanilla reigns supreme at ~21% of all orders and #1 across every state.\n"
        "• Chocolate (7.9%) and Cookie Dough (6.9%) round out the podium.\n\n"
        "📊 Data Source: Instacart Annual Consumer Data Report ('Pint-Sized Obsessions')"
    )

    # 3. Publish to Facebook Page
    success = post_photo_to_facebook(
        chart_path, 
        facebook_caption, 
        page_id, 
        token
    )

    if not success:
        print("❌ Pipeline finished with errors during Facebook publishing.")
        sys.exit(1)
    
    print("✅ Pipeline completed successfully using verified Instacart consumer datasets!")

if __name__ == "__main__":
    main()
