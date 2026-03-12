from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sys
import os
import threading
import secrets
import concurrent.futures
import traceback

# Add project root to path to import FILES modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from FILES.backend.db import init_db, register_user, authenticate, check_access, get_user_data, toggle_access, queue_command, get_pending_commands, delete_device



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
    name = data.get("name")
    device_username = data.get("device_username")
    password = data.get("password")
    browser_info = data.get("browser_info", "Unknown Device")
    
    if not name or not device_username or not password:
        return jsonify({"success": False, "error": "Name, Device Username, and Password required"}), 400
    
    result = register_user(name, device_username, password, browser_info)
    if "api_key" in result:
        return jsonify({"success": True, "message": f"Device {device_username} registered successfully", "api_key": result["api_key"]}), 201
    else:
        return jsonify({"success": False, "error": result.get("error", "Failed to register")}), 409

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Endpoint for user login with v5.0 sync logic."""
    print(f":> Accessing Login Page [{request.method}]")
    if request.method == 'GET':
        return render_template('login.html')
        
    data = request.json
    name = data.get("name")
    device_username = data.get("device_username")
    password = data.get("password")
    
    if authenticate(name, device_username, password):
        session['user_name'] = name
        session['device_username'] = device_username
        user_data = get_user_data(name)
        
        # Find the specific device API key to return
        api_key = None
        for device in user_data["devices"]:
            if device["device_username"] == device_username:
                api_key = device["api_key"]
                break
                
        return jsonify({
            "success": True, 
            "message": "Login successful",
            "user": {
                "name": name,
                "device_username": device_username,
                "api_key": api_key
            }
        }), 200
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/logout')
def logout():
    session.pop('user_name', None)
    session.pop('device_username', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    """Personal dashboard for users."""
    print(":> Accessing Dashboard [/dashboard]")
    if 'user_name' not in session:
        return redirect(url_for('login'))
        
    user_data = get_user_data(session['user_name'])
    return render_template('dashboard.html', user=user_data)

@app.route('/toggle_access', methods=['POST'])
def toggle():
    """API endpoint to toggle access from dashboard."""
    if 'user_name' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    data = request.json
    state = data.get("state") # Expected boolean
    target_device = data.get("device_username")
    if not target_device:
        return jsonify({"success": False, "error": "Target device not specified"}), 400
        
    toggle_access(session['user_name'], target_device, state)
    return jsonify({"success": True, "new_state": state}), 200

# Commands that non-admin users are allowed to send
PREDEFINED_COMMANDS = [
    'camera', 'screenshot', 'battery', 'brightness', 'location', 
    'wifi', 'bluetooth', 'volume', 'flash', 'lock', 'play_sound', 
    'get_apps', 'vibrate', 'toast'
]

# Sensitive keywords restricted to admin/coder
RESTRICTED_KEYWORDS = ['open', 'close', 'delete', 'start', 'shutdown', 'restart', 'play', 'shell', 'exec']
# Keywords that signal a session end
DISCONNECT_KEYWORDS = ['end', 'exit', 'quit']
        
import time
from collections import defaultdict

# --- API Protection & Rate Limiting ---
RATE_LIMIT_STRICT = 2.5  
RATE_LIMIT_GENERAL = 2.5 
user_last_request = defaultdict(float)

# --- ALFRED Device Polling Integration (v5.0) ---

@app.route('/api/<name>/<device_username>/', methods=['GET'])
def poll_device_commands(name, device_username):
    """Endpoint for ALFRED Local Listener to poll for commands."""
    api_key = request.args.get('api_key')
    if not api_key:
        return jsonify({"success": False, "error": "Missing api_key"}), 401
        
    # v1.0 Specific Rate Limiting (2.5s per device)
    device_key = f"{name}:{device_username}"
    now = time.time()
    last_time = user_last_request.get(device_key, 0)
    
    if now - last_time < RATE_LIMIT_GENERAL:
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
        
    user_last_request[device_key] = now
        
    pending_commands = get_pending_commands(name, device_username, api_key)
    
    if pending_commands is None:
        return jsonify({"success": False, "error": "Unauthorized or device not found."}), 403
        
    # Return list of command texts
    commands = [cmd["command"] for cmd in pending_commands]
    return jsonify(commands), 200

executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

# v1.0 Standard Rate Limit Check
def check_limit(key):
    now = time.time()
    last = user_last_request.get(key, 0)
    if now - last < RATE_LIMIT_GENERAL:
        return False
    user_last_request[key] = now
    return True

@app.route('/delete_device', methods=['POST'])
def remove_device():
    if 'user_name' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    data = request.json
    device_username = data.get("device_username")
    if not device_username:
        return jsonify({"success": False, "error": "Device name required"}), 400
    
    # Block deleting 'current_device' if it's the only one (optional, but let's allow it as requested)
    if delete_device(session['user_name'], device_username):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Deletion failed"}), 500
def execute():
    """Endpoint to queue a command for the local device listener."""
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
        name = None
        device_username = None
        
        # Priority 1: Use Web Session Context
        if 'user_name' in session:
            name = session['user_name']
            current_session_device = session.get('device_username')
            device_username = data.get("device_username") or current_session_device
            if not device_username:
                 return jsonify({"success": False, "error": "Target device not specified"}), 400
                 
            # v1.0 Security: Prevent sending to self if not admin
            is_admin = name.lower() in ["admin", "coder", "phone"]
            if (device_username == current_session_device or device_username == "current_device") and not is_admin:
                return jsonify({"success": False, "error": "Restricted: You cannot send commands to your own Current Device."}), 403
        else:
             return jsonify({"success": False, "error": "Not logged in"}), 401

        is_admin = name.lower() in ["admin", "coder", "phone"]
        is_predefined = any(p in command for p in PREDEFINED_COMMANDS)
        is_sensitive = any(keyword in command for keyword in RESTRICTED_KEYWORDS)
        
        # v1.0 Specific Rate Limiting (2.5s per device)
        device_key = f"{name}:{device_username}"
        now = time.time()
        last_time = user_last_request.get(device_key, 0)
        
        if now - last_time < RATE_LIMIT_GENERAL:
            return jsonify({"success": False, "error": "Rate limit exceeded. Please wait 2.5 seconds."}), 429
            
        user_last_request[device_key] = now
 
        # 4. Access Logic
        if not is_admin:
            if not is_predefined:
                 return jsonify({"success": False, "error": "Restricted: Only predefined commands allowed for non-admin accounts."}), 403
            if is_sensitive:
                 return jsonify({"success": False, "error": "Restricted: Admin authorization required for sensitive operations."}), 403

        # 5. Push to Device Queue
        success = queue_command(name, device_username, command)
        
        if success:
             return jsonify({"success": True, "user": name, "device": device_username, "command": command, "response": f"Command sent to {device_username}"}), 200
        else:
             return jsonify({"success": False, "error": "Failed to queue command."}), 500

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





def run_api():
    """Starts the Flask server for local debugging."""
    app.run(host="0.0.0.0", port=9000)

if __name__ == "__main__":
    run_api()
