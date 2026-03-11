from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sys
import os
import threading
import secrets
import concurrent.futures
import traceback

# Add project root to path to import FILES modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from FILES.backend.db import init_db, register_user, authenticate, check_access, get_user_data, toggle_access
from FILES.commands import process_command
from FILES.utils import Responder

# Ensure templates folder is recognized correctly
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
app = Flask(__name__, template_folder=template_dir)
app.secret_key = secrets.token_hex(24) # For session management

# Initialize DB globally for Serverless Vercel environments
init_db()

@app.route('/')
def home():
    """Serves the professional homepage."""
    print(":> Accessing Home Page [/]")
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Endpoint for user registration."""
    print(f":> Accessing Signup Page [{request.method}]")
    if request.method == 'GET':
        return render_template('signup.html')
        
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    
    api_key = register_user(username, password)
    if api_key:
        return jsonify({"success": True, "message": f"User {username} registered successfully", "api_key": api_key}), 201
    else:
        return jsonify({"success": False, "error": "User already exists"}), 409

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Endpoint for user login with v4.0 sync logic."""
    print(f":> Accessing Login Page [{request.method}]")
    if request.method == 'GET':
        return render_template('login.html')
        
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if authenticate(username, password):
        session['user'] = username
        user_data = get_user_data(username)
        return jsonify({
            "success": True, 
            "message": "Login successful",
            "user": {
                "username": user_data['username'],
                "api_key": user_data['api_key'],
                "has_access": bool(user_data['has_access'])
            }
        }), 200
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    """Personal dashboard for users."""
    print(":> Accessing Dashboard [/dashboard]")
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user_data = get_user_data(session['user'])
    return render_template('dashboard.html', user=user_data)

@app.route('/toggle_access', methods=['POST'])
def toggle():
    """API endpoint to toggle access from dashboard."""
    if 'user' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    data = request.json
    state = data.get("state") # Expected boolean
    toggle_access(session['user'], state)
    return jsonify({"success": True, "new_state": state}), 200

# Sensitive keywords restricted to admin/coder
RESTRICTED_KEYWORDS = ['open', 'close', 'delete', 'start', 'shutdown', 'restart', 'play']
# Keywords that signal a session end
DISCONNECT_KEYWORDS = ['end', 'exit', 'quit']
        
import time
from collections import defaultdict

# --- API Protection & Rate Limiting ---
RATE_LIMIT_STRICT = 2  # Seconds between requests for sensitive commands
RATE_LIMIT_GENERAL = 0.5 # Seconds for general chat
user_last_request = defaultdict(float)

# --- ALFRED Mobile Integration (v4.0) ---
import queue
mobile_commands = queue.Queue()

@app.route('/api/mobile/commands', methods=['GET'])
def poll_mobile_commands():
    """Endpoint for Android APK to poll for background commands."""
    commands_to_send = []
    try:
        # Drain the queue of all currently pending commands
        while not mobile_commands.empty():
            commands_to_send.append(mobile_commands.get_nowait())
    except queue.Empty:
        pass
        
    return jsonify(commands_to_send), 200

executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

def is_rate_limited(username, is_sensitive=False):
    """Check if a user is exceeding the rate limit."""
    now = time.time()
    last_time = user_last_request[username]
    limit = RATE_LIMIT_STRICT if is_sensitive else RATE_LIMIT_GENERAL
    if now - last_time < limit:
        return True
    user_last_request[username] = now
    return False

@app.route('/execute', methods=['POST'])
def execute():
    """Endpoint to execute a command with threaded performance v3.1."""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400
            
        command = data.get("command", "").lower().strip()
        if not command:
            return jsonify({"success": False, "error": "Empty command"}), 400

        # 1. Handle Disconnect/Exit logic
        if any(k in command for k in DISCONNECT_KEYWORDS):
            print(f":> Termination Requested: {command}")
            return jsonify({"success": True, "disconnect": True, "response": "Disconnecting session..."}), 200

        # 2. Identify Role and Credentials
        username = None
        api_key = data.get("api_key")
        
        # Priority 1: API Key based session authentication (v3.0 standard)
        if api_key:
            # We need to find the user by API Key if username isn't provided or is untrusted
            # Small helper to find user by key in DB would be better, but we'll use existing get_user_data with session if available
            if 'user' in session:
                username = session['user']
            else:
                # If no session, we require username for now to resolve the key
                username = data.get("username")
            
            if not username:
                return jsonify({"success": False, "error": "Username required to validate API key"}), 401
                
            user_data = get_user_data(username)
            if not user_data or user_data['api_key'] != api_key:
                return jsonify({"success": False, "error": "Invalid API Key or Username"}), 403
        else:
            # Priority 2: Traditional Session/Credential Auth
            if 'user' in session:
                username = session['user']
                user_data = get_user_data(username)
                api_key = user_data['api_key']
            else:
                username = data.get("username")
                password = data.get("password")
                if not username or not password:
                    return jsonify({"success": False, "error": "Credentials or API Key required"}), 401
                if not authenticate(username, password):
                     return jsonify({"success": False, "error": "Unauthorized"}), 403
                user_data = get_user_data(username)
                api_key = user_data['api_key']

        is_admin = username.lower() in ["admin", "coder", "phone"]
        is_sensitive = any(keyword in command for keyword in RESTRICTED_KEYWORDS)

        # 3. Rate Limiting Protection
        if is_rate_limited(username, is_sensitive):
            return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
 
        # 4. Tiered Access Logic
        if is_sensitive and not is_admin:
            print(f":> Restricted Access Blocked: {username} tried '{command}'")
            return jsonify({"success": False, "error": f"Restricted: Admin only."}), 403

        # 5. Access Enable Check (Dashboard Toggle)
        if not check_access(username, api_key):
            return jsonify({"success": False, "error": "Access Disabled"}), 403

        # 6. Mobile Command Routing (v4.0)
        mobile_actions = {
            "message": "send_sms",
            "sms": "send_sms",
            "call": "make_call",
            "dial": "make_call",
            "launch": "launch_app",
            "open app": "launch_app",
            "bluetooth": "set_bluetooth",
            "wifi": "set_wifi",
            "volume": "set_volume",
            "browse": "open_browser",
            "open web": "open_browser",
            "open url": "open_browser",
            "url": "open_browser"
        }
        
        # Check if the command starts with a mobile action
        for k, action_type in mobile_actions.items():
            if command.startswith(k):
                # Extract payload
                payload_val = command.replace(k, "").strip()
                cmd_payload = {}
                
                if action_type == "launch_app": 
                    cmd_payload = {"package": payload_val}
                elif action_type == "open_browser":
                    # Ensure url starts with http if not provided
                    url = payload_val if payload_val.startswith("http") else f"https://{payload_val}"
                    cmd_payload = {"url": url}
                elif action_type in ["set_bluetooth", "set_wifi"]: 
                    cmd_payload = {"enabled": payload_val}
                elif action_type == "set_volume":
                    cmd_payload = {"level": payload_val}
                elif action_type == "send_sms":
                    parts = payload_val.split(" ", 1)
                    if len(parts) == 2:
                        cmd_payload = {"number": parts[0], "message": parts[1]}
                    else:
                        cmd_payload = {"number": payload_val, "message": "ALFRED command ping."}
                else:
                    cmd_payload = {"number": payload_val}
                
                cmd_obj = {
                    "action": action_type,
                    "payload": cmd_payload
                }
                mobile_commands.put(cmd_obj)
                print(f":> [MOBILE ROUTING] Sent to phone: {cmd_obj}")
                return jsonify({"success": True, "response": f"Command sent to mobile device: {command}"}), 200

        # 7. Threaded Execution (v3.1)
        def run_command():
            print(f":> [THREAD] Executing: {username} -> {command}")
            res = process_command(command)
            if not res or res.lower().startswith("i don't understand"):
                res = Responder(command)
            return res

        future = executor.submit(run_command)
        response = future.result(timeout=180) # Wait for result but run in threadpool

        return jsonify({"success": True, "user": username, "command": command, "response": response}), 200

    except Exception as e:
        print(f":> [CRITICAL] Internal Error: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": "Internal Server Error"}), 500



def run_api():
    """Starts the Flask server for local network access."""
    init_db()
    
    # Disable Flask banner to avoid Windows Error 6
    import flask.cli
    flask.cli.show_server_banner = lambda *args: None
    
    print(":> ALFRED Web System [v2.1] starting on http://0.0.0.0:5000")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f":> API Server Error: {e}")

if __name__ == "__main__":
    run_api()




