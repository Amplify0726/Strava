from flask import Blueprint, request, jsonify
import os, requests, datetime

# Define Blueprint
webhook_bp = Blueprint('webhook', __name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def strava_webhook():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return jsonify({'hub.challenge': request.args.get('hub.challenge')})
        return "Invalid verification token", 403

    if request.method == 'POST':
        event = request.json
        if event['object_type'] == 'activity' and event['aspect_type'] == 'create':
            activity_id = event['object_id']
            handle_new_activity(activity_id)
        return '', 200

def handle_new_activity(activity_id):
    access_token = os.getenv('STRAVA_ACCESS_TOKEN')
    if not access_token:
        print("No access token.")
        return

    # Get current activity details
    resp = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={'Authorization': f'Bearer {access_token}'}
    )
    activity = resp.json()
    current_description = activity.get('description', '') or ''

    # Strip out any previous totals you may have added
    separator = "\n\n7-day totals:"
    if separator in current_description:
        current_description = current_description.split(separator)[0].strip()

    # Get past 7 days of activities
    now = datetime.datetime.utcnow()
    after = int((now - datetime.timedelta(days=7)).timestamp())
    activities = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'after': after, 'per_page': 200}
    ).json()

    # Calculate totals
    total_distance = sum(a.get('distance', 0) for a in activities) / 1000
    total_time = sum(a.get('moving_time', 0) for a in activities) / 60
    total_elev = sum(a.get('total_elevation_gain', 0) for a in activities)

    # Build totals text
    totals_text = (
        f"7-day totals:\n"
        f"🏃 {total_distance:.2f} km\n"
        f"⏱️ {total_time:.1f} min\n"
        f"⛰️ {total_elev:.1f} m"
    )

    # Append to description
    new_description = f"{current_description}\n\n{totals_text}".strip()

    # Update the activity
    requests.put(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={'Authorization': f'Bearer {access_token}'},
        data={'description': new_description}
    )
