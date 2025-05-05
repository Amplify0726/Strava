from flask import Flask, redirect, request, session, jsonify
import requests
import datetime
import hashlab
import hmac

app = Flask(__name__)
app.secret_key = 'your_secret'

CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'http://localhost:5000/callback'

@app.route('/')
def home():
	return redirect(
		f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=auto&scope=activity:read_all, activity:write"
	)

@app.route('/webhook', methods=['GET', 'POST'])
def strava_webhook():
	if request.method == 'GET':
		# Strava webhook verification handshake
		if request.args.get('hub.verify_token') == VERIFY_TOKEN:
			return jsonify({
				'hub.challenge': request.args.get('hub.challenge')
			})
		return "Invalid verification token", 403

	if request.method == 'POST':
		event = request.json

		# Only trigger on new activity
		if event['aspect_type'] == 'create' and event['object_type'] == 'activity':
			# Optionally filter only the authenticated user’s activities
			activity_id = event['object_id']
			owner_id = event['owner_id']
			# You can queue a task or process directly:
			handle_new_activity(activity_id)

		return '', 200
def handle_new_activity(activity_id):
	token = session.get('access_token')
	if not token:
		print("No token in session.")
		return

	# Get activity details
	resp = requests.get(
		f"https://www.strava.com/api/v3/activities/{activity_id}",
		headers={'Authorization': f'Bearer {token}'}
	)
	activity = resp.json()

	# Fetch past 7-day activities
	now = datetime.datetime.utcnow()
	after = int((now - datetime.timedelta(days=7)).timestamp())

	activities = requests.get(
		"https://www.strava.com/api/v3/athlete/activities",
		headers={'Authorization': f'Bearer {token}'},
		params={'after': after, 'per_page': 200}
	).json()

	total_distance = sum(a.get('distance', 0) for a in activities) / 1000
	total_time = sum(a.get('moving_time', 0) for a in activities) / 60
	total_elev = sum(a.get('total_elevation_gain', 0) for a in activities)

	totals_text = (
		f"7-day totals:\n"
		f"🏃 {total_distance:.2f} km\n"
		f"⏱️ {total_time:.1f} min\n"
		f"⛰️ {total_elev:.1f} m"
	)

	new_description = f"{activity.get('description', '')}\n\n{totals_text}".strip()

	# Update description
	requests.put(
		f"https://www.strava.com/api/v3/activities/{activity_id}",
		headers={'Authorization': f'Bearer {token}'},
		data={'description': new_description}
	)


@app.route('/callback')
def callback():
	code = request.args.get('code')
	response = requests.post(
		"https://www.strava.com/oauth/token",
		data={
			'client_id': CLIENT_ID,
			'client_secret': CLIENT_SECRET,
			'code': code,
			'grant_type': 'authorization_code'
		}
	).json()
	session['access_token'] = response['access_token']
	return redirect('/totals')

@app.route('/totals')
def totals():
	token = session.get('access_token')
	if not token:
		return redirect('/')
	
	# Get activities from past 7 days
	now = datetime.datetime.utcnow()
	after = int((now - datetime.timedelta(days=7)).timestamp())

	activities = requests.get(
		"https://www.strava.com/api/v3/athlete/activities",
		headers={'Authorization': f'Bearer {token}'},
		params={'after': after, 'per_page': 200}
	).json()

	# Calculate totals
	total_distance = sum(act.get('distance', 0) for act in activities)
	total_time = sum(act.get('moving_time', 0) for act in activities)
	total_elev = sum(act.get('total_elevation_gain', 0) for act in activities)

	# Return rolling totals
	return jsonify({
		"7_day_total_distance_km": round(total_distance / 1000, 2),
		"7_day_total_moving_time_min": round(total_time / 60, 2),
		"7_day_total_elevation_gain_m": round(total_elev, 2)
	})

if __name__ == '__main__':
	app.run(debug=True)
