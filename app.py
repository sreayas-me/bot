from flask import Flask, render_template, redirect, request, make_response, url_for, jsonify
from werkzeug.serving import make_server
import requests
import json
from functools import wraps
import time
from utils.db import db

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
        resp.set_cookie('access_token', access_token)  # Store access token in cookie
        return resp
    return 'Authentication failed', 400

@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.delete_cookie('user_id')
    resp.delete_cookie('username')
    resp.delete_cookie('access_token')  # Remove access token cookie
    return resp

def get_user_guilds(access_token):
    """Fetch user's Discord servers"""
    response = requests.get('https://discord.com/api/users/@me/guilds', headers={
        'Authorization': f'Bearer {access_token}'
    })
    if response.status_code == 200:
        return response.json()
    return []

def get_bot_guilds():
    """Fetch bot's server list from stats"""
    global bot_stats
    return bot_stats.get('guilds', [])

@app.route('/servers')
@login_required
def servers():
    """Show list of servers the user has access to"""
    access_token = request.cookies.get('access_token')
    if not access_token:
        return redirect('/login')
        
    user_guilds = get_user_guilds(access_token)
    bot_guilds = get_bot_guilds()
    
    # Filter guilds where user has manage server permission
    manage_guilds = [
        guild for guild in user_guilds 
        if (int(guild['permissions']) & 0x20) == 0x20  # Check for MANAGE_GUILD permission
    ]
    
    # Mark guilds where bot is present
    for guild in manage_guilds:
        guild['bot_present'] = guild['id'] in bot_guilds
        
    return render_template('servers.html', 
        guilds=manage_guilds,
        username=request.cookies.get('username', 'User'),
        config={'CLIENT_ID': DISCORD_CLIENT_ID}
    )

@app.route('/servers/<guild_id>/settings')
@login_required
async def server_settings(guild_id):
    """Show settings for a specific server"""
    access_token = request.cookies.get('access_token')
    if not access_token:
        return redirect('/login')
        
    # Verify user has access to this server
    user_guilds = get_user_guilds(access_token)
    if not any(g['id'] == guild_id and (int(g['permissions']) & 0x20) == 0x20 for g in user_guilds):
        return "Unauthorized", 403
        
    # Get server settings from database
    settings = await db.get_guild_settings(guild_id)
    
    # Get guild info from Discord
    guild_info = next((g for g in user_guilds if g['id'] == guild_id), None)
    
    return render_template('settings.html',
        guild=guild_info,
        settings=settings,
        username=request.cookies.get('username', 'User')
    )

@app.route('/servers/<guild_id>/settings/update', methods=['POST'])
@login_required
async def update_settings(guild_id):
    """Update settings for a specific server"""
    access_token = request.cookies.get('access_token')
    if not access_token:
        return redirect('/login')
        
    # Verify user has access to this server
    user_guilds = get_user_guilds(access_token)
    if not any(g['id'] == guild_id and (int(g['permissions']) & 0x20) == 0x20 for g in user_guilds):
        return "Unauthorized", 403
        
    # Get settings from form
    settings = {
        'prefixes': request.form.getlist('prefixes'),
        'welcome': {
            'enabled': bool(request.form.get('welcome_enabled')),
            'channel_id': request.form.get('welcome_channel'),
            'message': request.form.get('welcome_message')
        },
        'moderation': {
            'log_channel': request.form.get('log_channel'),
            'mute_role': request.form.get('mute_role'),
            'jail_role': request.form.get('jail_role')
        }
    }
    
    # Update database
    await db.update_guild_settings(guild_id, settings)
    
    return redirect(f'/servers/{guild_id}/settings')

@app.route('/settings')
@login_required
def settings_select():
    """Show server selection for settings"""
    access_token = request.cookies.get('access_token')
    if not access_token:
        return redirect('/login')
        
    user_guilds = get_user_guilds(access_token)
    bot_guilds = get_bot_guilds()
    
    # Filter guilds where user has manage server permission
    manage_guilds = [
        guild for guild in user_guilds 
        if (int(guild['permissions']) & 0x20) == 0x20
    ]
    
    # Add bot presence info
    for guild in manage_guilds:
        guild['bot_present'] = str(guild['id']) in bot_guilds
        guild['icon_url'] = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild['icon'] else None
    
    return render_template('settings_select.html',
        guilds=manage_guilds,
        username=request.cookies.get('username', 'User')
    )

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

