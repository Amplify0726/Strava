from flask import Flask, request, jsonify
import requests
import datetime
import os
import time
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if available
except ImportError:
    print("python-dotenv not installed, skipping .env loading")

from token_manager import TokenManager

app = Flask(__name__)

# Get credentials from environment variables
CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
VERIFY_TOKEN = os.getenv('STRAVA_VERIFY_TOKEN')
REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')

# Print environment variables for debugging (exclude sensitive info)
print(f"STRAVA_CLIENT_ID set: {'Yes' if CLIENT_ID else 'No'}")
print(f"STRAVA_CLIENT_SECRET set: {'Yes' if CLIENT_SECRET else 'No'}")
print(f"STRAVA_REFRESH_TOKEN set: {'Yes' if REFRESH_TOKEN else 'No'}")
print(f"STRAVA_VERIFY_TOKEN set: {'Yes' if VERIFY_TOKEN else 'No'}")

# Initialize the token manager
token_manager = TokenManager(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

@app.route('/')
def home():
    return "Strava webhook service is running!"

@app.route('/webhook', methods=['GET', 'POST'])
def strava_webhook():
    if request.method == 'GET':
        # Strava webhook verification handshake
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if token == VERIFY_TOKEN:
            print(f"Webhook verified with challenge: {challenge}")
            return jsonify({'hub.challenge': challenge})
        else:
            print(f"Invalid verification token: {token}")
            return "Invalid verification token", 403

    if request.method == 'POST':
        event = request.json
        print(f"Received webhook event: {event}")
        
        # Check if this is an activity creation event
        if event.get('object_type') == 'activity' and event.get('aspect_type') == 'create':
            activity_id = event.get('object_id')
            handle_new_activity(activity_id)
            
        return '', 200

def handle_new_activity(activity_id, retry_attempt=0, max_retries=3):
    try:
        print(f"Processing activity {activity_id}")
        # Get a fresh access token
        access_token = token_manager.get_access_token()
        
        # Get activity details
        resp = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        resp.raise_for_status()
        activity = resp.json()
        
        # Get current description, handle None case
        current_description = activity.get('description', '') or ''

        # Check if totals already exist
        if "7-day rolling totals:" in current_description:
            print(f"Activity {activity_id} already has totals, skipping")
            return True  # Return True to indicate successful handling

        # Get past 7 days of activities
        now = datetime.datetime.utcnow()
        after = int((now - datetime.timedelta(days=7)).timestamp())
        
        activities_resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={'Authorization': f'Bearer {access_token}'},
            params={'after': after, 'per_page': 200}
        )
        activities_resp.raise_for_status()
        activities = activities_resp.json()

        # Filter for only Run and TrailRun activities
        run_activities = [a for a in activities if a.get('type') in ['Run', 'TrailRun']]
        print(f"Found {len(run_activities)} runs out of {len(activities)} total activities in last 7 days")

        # Calculate totals
        total_distance = sum(a.get('distance', 0) for a in run_activities) / 1000
        total_time_seconds = sum(a.get('moving_time', 0) for a in run_activities)
        total_elev = sum(a.get('total_elevation_gain', 0) for a in run_activities)

        # Convert time to hours and minutes
        hours = int(total_time_seconds // 3600)
        minutes = int((total_time_seconds % 3600) // 60)

        # Build totals text
        totals_text = (
            f"7-day rolling totals:\n"
            f"🏃 {total_distance:.2f} km\n"
            f"⏱️ {hours}h {minutes}m\n"
            f"⛰️ {total_elev:.1f} m"
        )

        # Append to description
        new_description = f"{current_description}\n\n{totals_text}".strip()

        # Update the activity
        update_resp = requests.put(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={'Authorization': f'Bearer {access_token}'},
            data={'description': new_description}
        )
        update_resp.raise_for_status()
        print(f"Successfully updated activity {activity_id} with 7-day totals")
        
    except Exception as e:
        print(f"Error handling activity {activity_id}: {e}")
        if retry_attempt < max_retries - 1:
            print(f"Retrying activity {activity_id} in 5 seconds... (attempt {retry_attempt + 2}/{max_retries})")
            time.sleep(5)
            return handle_new_activity(activity_id, retry_attempt=retry_attempt+1, max_retries=max_retries)
        else:
            print(f"Activity {activity_id} failed after {max_retries} attempts.")
            return False

@app.route('/test_token')
def test_token():
    """Endpoint to test token refresh"""
    try:
        token = token_manager.get_access_token()
        return jsonify({
            "status": "success", 
            "message": "Token retrieved successfully", 
            "token_preview": token[:5] + "..." + token[-5:],
            "expires_at": datetime.datetime.fromtimestamp(token_manager.expires_at).isoformat() if hasattr(token_manager, 'expires_at') else "Unknown"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)