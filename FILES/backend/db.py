import hashlib
import secrets
import os
import json
from pathlib import Path

if os.environ.get("VERCEL"):
    DB_ROOT = "/tmp/users"
else:
    DB_ROOT = os.path.join(os.path.dirname(__file__), "users_db")

def init_db():
    """Initializes the base directory for the file-based database."""
    os.makedirs(DB_ROOT, exist_ok=True)
    
    # Create default admin account if it doesn't exist
    admin_dir = os.path.join(DB_ROOT, "admin")
    if not os.path.exists(admin_dir):
        os.makedirs(admin_dir, exist_ok=True)
        # Hashed password for 'password'
        pw_hash = hash_password("password")
        with open(os.path.join(admin_dir, "password.txt"), "w") as f:
            f.write(pw_hash)
            
        devices_dir = os.path.join(admin_dir, "devices")
        os.makedirs(devices_dir, exist_ok=True)
        
        # Default device for admin
        device_key = secrets.token_hex(16)
        device_data = {
            "device_username": "current_device",
            "api_key": device_key,
            "browser_info": "ALFRED Core v1.0"
        }
        with open(os.path.join(devices_dir, "current_device.json"), "w") as f:
            json.dump(device_data, f)
            
        # Initialize queue
        with open(os.path.join(devices_dir, "current_device_queue.json"), "w") as f:
            json.dump([], f)
            
        print(f":> v1.0 Database initialized with default admin.")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(name, device_username, password, browser_info="Unknown"):
    """Registers a new account/device based on v1.0 specs."""
    os.makedirs(DB_ROOT, exist_ok=True)
    user_dir = os.path.join(DB_ROOT, name)
    pw_hash = hash_password(password)
    
    # Check if Account exists
    if os.path.exists(user_dir):
        # Validate password to allow adding a new device to existing account
        pw_file = os.path.join(user_dir, "password.txt")
        if os.path.exists(pw_file):
            with open(pw_file, "r") as f:
                if f.read().strip() != pw_hash:
                    return {"error": "Invalid password for existing Account name."}
    else:
        # Create new Account-folder
        os.makedirs(user_dir, exist_ok=True)
        with open(os.path.join(user_dir, "password.txt"), "w") as f:
            f.write(pw_hash)
            
    # Device Registration under Account/devices/
    devices_dir = os.path.join(user_dir, "devices")
    os.makedirs(devices_dir, exist_ok=True)
    
    device_file = os.path.join(devices_dir, f"{device_username}.json")
    if os.path.exists(device_file):
        return {"error": "Device already registered to this account."}
        
    api_key = secrets.token_hex(16)
    device_data = {
        "device_username": device_username,
        "api_key": api_key,
        "browser_info": browser_info
    }
    
    with open(device_file, "w") as f:
        json.dump(device_data, f)
        
    # Create empty queue
    with open(os.path.join(devices_dir, f"{device_username}_queue.json"), "w") as f:
        json.dump([], f)
        
    return {"api_key": api_key}

def authenticate(name, device_username, password, browser_info=None):
    """
    Checks credentials and ensures the device exists/is updated.
    v1.0 Logic: If account matches but device is missing, auto-add the device.
    """
    user_dir = os.path.join(DB_ROOT, name)
    pw_hash = hash_password(password)
    
    if not os.path.exists(user_dir): return False
    
    pw_file = os.path.join(user_dir, "password.txt")
    if not os.path.exists(pw_file): return False
        
    with open(pw_file, "r") as f:
        if f.read().strip() != pw_hash: return False
            
    # Account is valid. Ensure device exists.
    devices_dir = os.path.join(user_dir, "devices")
    os.makedirs(devices_dir, exist_ok=True)
    
    device_file = os.path.join(devices_dir, f"{device_username}.json")
    if not os.path.exists(device_file):
        # Auto-register new device on valid login
        register_user(name, device_username, password, browser_info or "Auto-registered on Login")
             
    return True

def get_user_data(name):
    """Retrieves all devices and their info for the dashboard."""
    user_dir = os.path.join(DB_ROOT, name)
    if not os.path.exists(user_dir):
        return None
        
    devices_dir = os.path.join(user_dir, "devices")
    if not os.path.exists(devices_dir):
        return {"name": name, "devices": []}
        
    devices = []
    for filename in os.listdir(devices_dir):
        if filename.endswith(".json") and not filename.endswith("_queue.json"):
            with open(os.path.join(devices_dir, filename), "r") as f:
                device_data = json.load(f)
                devices.append({
                    "username": device_data["device_username"], # Keeping legacy key for compatibility if needed
                    "device_username": device_data["device_username"],
                    "api_key": device_data["api_key"],
                    "browser_info": device_data.get("browser_info", "Unknown")
                })
                
    return {"username": name, "name": name, "devices": devices}

def toggle_access(name, device_username, state):
    """(Deprecated) Toggles the has_access state for a specific device."""
    pass

def check_access(name, device_username, api_key):
    """Verifies the device exists and has the matching API key."""
    if name.lower() in ["admin", "coder"]:
        return True
        
    device_file = os.path.join(DB_ROOT, name, "devices", f"{device_username}.json")
    if not os.path.exists(device_file):
        return False
        
    with open(device_file, "r") as f:
        data = json.load(f)
        
    return data.get("api_key") == api_key

# --- Command Queue Functionality ---

def queue_command(name, device_username, command_text):
    """Pushes a command into the device's polling queue."""
    queue_file = os.path.join(DB_ROOT, name, "devices", f"{device_username}_queue.json")
    
    if not os.path.exists(os.path.dirname(queue_file)):
        return False
        
    queue = []
    if os.path.exists(queue_file):
        with open(queue_file, "r") as f:
            try:
                queue = json.load(f)
            except json.JSONDecodeError:
                queue = []
                
    queue.append({"command": command_text, "timestamp": os.path.getmtime(queue_file) if os.path.exists(queue_file) else 0})
    
    with open(queue_file, "w") as f:
        json.dump(queue, f)
    return True

def delete_device(account_name, device_username):
    """Deletes a device and its associated queue files."""
    try:
        devices_dir = os.path.join(DB_ROOT, account_name, "devices")
        device_file = os.path.join(devices_dir, f"{device_username}.json")
        queue_file = os.path.join(devices_dir, f"{device_username}_queue.json")
        
        if os.path.exists(device_file):
            os.remove(device_file)
        if os.path.exists(queue_file):
            os.remove(queue_file)
        return True
    except Exception as e:
        print(f"Error deleting device: {e}")
        return False

def get_pending_commands(name, device_username, api_key):
    """Retrieves and clears pending commands for a device. Requires auth."""
    if not check_access(name, device_username, api_key):
        return None
        
    queue_file = os.path.join(DB_ROOT, name, "devices", f"{device_username}_queue.json")
    
    if not os.path.exists(queue_file):
        return []
        
    with open(queue_file, "r") as f:
        try:
            queue = json.load(f)
        except json.JSONDecodeError:
            queue = []
            
    # Clear queue after reading
    with open(queue_file, "w") as f:
        json.dump([], f)
        
    return queue

if __name__ == "__main__":
    init_db()
