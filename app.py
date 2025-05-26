from flask import Flask, render_template, redirect, request, make_response, url_for, jsonify
from werkzeug.serving import make_server
import requests
import json
from functools import wraps
import time

app = Flask(__name__)
server = None

# Load config
with open("data/config.json", "r") as f:
    config = json.load(f)

DISCORD_CLIENT_ID = config['CLIENT_ID']
DISCORD_CLIENT_SECRET = config['CLIENT_SECRET']
DISCORD_REDIRECT_URI = 'http://localhost:5000/callback'
DISCORD_BOT_OWNER_ID = config['OWNER_ID']

# Global stats dictionary
bot_stats = {
    'server_count': 0,
    'user_count': 0,
    'uptime': 0,
    'latency': 0
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.cookies.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/stats', methods=['GET', 'POST'])
def api_stats():
    global bot_stats
    if request.method == 'POST':
        bot_stats.update(request.json)
        return jsonify({"status": "success"})
    return jsonify(bot_stats)

@app.route('/')
def home():
    user_id = request.cookies.get('user_id')
    if user_id and user_id == DISCORD_BOT_OWNER_ID:
        username = request.cookies.get('username', 'User')
        return render_template('index.html', username=username, stats=bot_stats)
    return render_template('home.html')

@app.route('/login')
def login():
    return redirect(f'https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': 'identify'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    if response.status_code == 200:
        credentials = response.json()
        access_token = credentials['access_token']
        
        # Get user info
        user_response = requests.get('https://discord.com/api/users/@me', headers={
            'Authorization': f'Bearer {access_token}'
        })
        user = user_response.json()
        
        resp = make_response(redirect('/'))
        resp.set_cookie('user_id', user['id'])
        resp.set_cookie('username', user['username'])
        return resp
    return 'Authentication failed', 400

@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.delete_cookie('user_id')
    resp.delete_cookie('username')
    return resp

def run_server():
    global server
    server = make_server('127.0.0.1', 5000, app)
    server.serve_forever()

def shutdown_server():
    global server
    if server:
        server.shutdown()

def run():
    run_server()

if __name__ == "__main__":
    run()

