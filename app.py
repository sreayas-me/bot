from flask import Flask, render_template, redirect, request, make_response, url_for, jsonify
import requests
import json
from functools import wraps
import time
import os
from utils.db import db  # This now uses the synchronous databasek import Flask, render_template, redirect, request, make_response, url_for, jsonify
from werkzeug.serving import make_server
import asyncio
import functools
import requests
import json
from functools import wraps
import time
from utils.db import db  # This now uses the synchronous # For local development
def run():
    app.run(host='127.0.0.1', port=5000)

def shutdown_server():
    pass

if __name__ == "__main__":
    app = Flask(__name__)

# Add thousands filter
@app.template_filter('thousands')
def thousands_filter(value):
    """Format a number with thousands separator"""
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return "0"

# Load config from environment variables or config file
try:
    DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
    DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
    DISCORD_BOT_OWNER_ID = os.environ.get('DISCORD_BOT_OWNER_ID')
    
    # If env vars not set, try config file
    if not all([DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_OWNER_ID]):
        with open("data/config.json", "r") as f:
            config = json.load(f)
        DISCORD_CLIENT_ID = DISCORD_CLIENT_ID or config['CLIENT_ID']
        DISCORD_CLIENT_SECRET = DISCORD_CLIENT_SECRET or config['CLIENT_SECRET']
        DISCORD_BOT_OWNER_ID = DISCORD_BOT_OWNER_ID or config['OWNER_ID']
        
except Exception as e:
    print(f"Error loading configuration: {e}")
    raise

# Set callback URI based on environment
if os.environ.get('RENDER_EXTERNAL_URL'):
    DISCORD_REDIRECT_URI = f"{os.environ['RENDER_EXTERNAL_URL']}/callback"
else:
    DISCORD_REDIRECT_URI = 'http://localhost:5000/callback'

# Global stats dictionary
bot_stats = {
    'server_count': 0,
    'user_count': 0,
    'uptime': 0,
    'latency': 0,
    'guilds': []  # List of guild IDs where bot is present
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
    return render_template('home.html', stats=bot_stats, config=config)

@app.route('/login')
def login():
    return redirect(f'https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify+guilds')

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
    
    # Mark guilds where bot is present and add icon URLs
    for guild in manage_guilds:
        guild['bot_present'] = str(guild['id']) in bot_guilds
        guild['icon_url'] = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild['icon'] else None
    
    # Sort guilds to show bot-present servers first
    manage_guilds.sort(key=lambda g: (not g['bot_present'], g['name'].lower()))
    
    return render_template('servers.html', 
        guilds=manage_guilds,
        username=request.cookies.get('username', 'User'),
        config={'CLIENT_ID': DISCORD_CLIENT_ID}
    )

@app.route('/servers/<guild_id>/settings')
@login_required
def server_settings(guild_id):
    """Show settings for a specific server"""
    access_token = request.cookies.get('access_token')
    if not access_token:
        return redirect('/login')
        
    # Verify user has access to this server
    user_guilds = get_user_guilds(access_token)
    if not any(g['id'] == guild_id and (int(g['permissions']) & 0x20) == 0x20 for g in user_guilds):
        return "Unauthorized", 403

    # Get server settings from database
    settings = db.get_guild_settings(guild_id)
    
    # Get guild info from Discord API
    headers = {'Authorization': f'Bot {config["TOKEN"]}'}
    guild_response = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}', headers=headers)
    channels_response = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/channels', headers=headers)
    roles_response = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/roles', headers=headers)
    
    guild_info = guild_response.json() if guild_response.ok else None
    channels = channels_response.json() if channels_response.ok else []
    roles = roles_response.json() if roles_response.ok else []
    
    # Filter text channels only and sort by position
    text_channels = sorted(
        [c for c in channels if c['type'] == 0],  # 0 is text channel
        key=lambda c: c.get('position', 0)
    )
    
    # Sort roles by position
    roles = sorted(roles, key=lambda r: r.get('position', 0), reverse=True)
    
    return render_template('settings.html',
        guild=guild_info,
        settings=settings,
        channels=text_channels,
        roles=roles,
        username=request.cookies.get('username', 'User')
    )

@app.route('/servers/<guild_id>/settings/update', methods=['POST'])
@login_required
def update_settings(guild_id):
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
        'prefixes': [p.strip() for p in request.form.get('prefixes', '').split(',') if p.strip()],  # Fix prefix splitting
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
    
    # Update database (now synchronous)
    success = db.update_guild_settings(guild_id, settings)
    
    if success:
        return redirect(f'/servers/{guild_id}/settings?success=1')
    else:
        return redirect(f'/servers/{guild_id}/settings?error=1')

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
    
    # Sort guilds to show bot-present servers first
    manage_guilds.sort(key=lambda g: (not g['bot_present'], g['name'].lower()))
    
    return render_template('settings_select.html',
        guilds=manage_guilds,
        username=request.cookies.get('username', 'User'),
        config={'CLIENT_ID': DISCORD_CLIENT_ID}
    )

@app.route('/api/user/<user_id>/balance')
@login_required
def get_user_balance(user_id):
    """API endpoint to get user balance"""
    # Only allow the user to see their own balance or allow bot owner to see any balance
    requester_id = request.cookies.get('user_id')
    if requester_id != user_id and requester_id != DISCORD_BOT_OWNER_ID:
        return jsonify({"error": "Unauthorized"}), 403
    
    balance = db.get_user_balance(user_id)
    return jsonify(balance)

@app.route('/api/guild/<guild_id>/stats')
@login_required
def get_guild_stats(guild_id):
    """API endpoint to get guild stats"""
    access_token = request.cookies.get('access_token')
    if not access_token:
        return jsonify({"error": "No access token"}), 401
        
    # Verify user has access to this server
    user_guilds = get_user_guilds(access_token)
    if not any(g['id'] == guild_id and (int(g['permissions']) & 0x20) == 0x20 for g in user_guilds):
        return jsonify({"error": "Unauthorized"}), 403
    
    stats = db.get_guild_stats(guild_id)
    return jsonify(stats)

@app.route('/debug')
def debug():
    """Debug endpoint to check application status"""
    return jsonify({
        'status': 'ok',
        'env': os.environ.get('FLASK_ENV'),
        'discord_configured': bool(DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET),
        'redirect_uri': DISCORD_REDIRECT_URI
    })

def create_app():
    app = Flask(__name__)
    
    # Add thousands filter
    @app.template_filter('thousands')
    def thousands_filter(value):
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return "0"

    # Configure for production
    app.config['SERVER_NAME'] = None
    
    return app

app = create_app()

def run():
    """Development server in a thread for the Discord bot"""
    import threading
    def run_server():
        app.run(host='127.0.0.1', port=5000)
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("Web server started on http://localhost:5000")

def shutdown_server():
    pass

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    if os.environ.get('FLASK_ENV') == 'production':
        # Production mode (Render)
        app.run(host='0.0.0.0', port=port)
    else:
        # Development mode
        app.run(host='127.0.0.1', port=5000, debug=True)