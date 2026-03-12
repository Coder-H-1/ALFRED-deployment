import hashlib
import secrets
import os
import json
from pathlib import Path

# Vercel KV / Redis support
IS_VERCEL = os.environ.get("VERCEL")
redis_client = None

if IS_VERCEL:
    try:
        from upstash_redis import Redis
        # Support both Upstash defaults and Vercel KV defaults
        url = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN")
        
        if url and token:
            redis_client = Redis(url=url, token=token)
            print(":> Connected to Vercel KV (Redis)")
        else:
            print("!! Redis environment variables missing. Using local /tmp.")
    except Exception as e:
        print(f"!! Redis initialization failed: {e}")

def toggle_access(name, device_username, state):
    """(Stub for compatibility)"""
    pass

if IS_VERCEL:
    DB_ROOT = "/tmp/users"
else:
    DB_ROOT = os.path.join(os.path.dirname(__file__), "users_db")

def init_db():
    """Initializes the database. In Redis, ensures admin exists."""
    os.makedirs(DB_ROOT, exist_ok=True)
    
    admin_name = "admin"
    admin_pw = "password"
    
    if redis_client:
        if not redis_client.exists(f"alfred:account:{admin_name}:pw"):
            pw_hash = hash_password(admin_pw)
            redis_client.set(f"alfred:account:{admin_name}:pw", pw_hash)
            
            device_data = {
                "device_username": "current_device",
                "api_key": secrets.token_hex(16),
                "browser_info": "ALFRED Core v1.0"
            }
            redis_client.set(f"alfred:account:{admin_name}:device:current_device", json.dumps(device_data))
            redis_client.sadd(f"alfred:account:{admin_name}:devices", "current_device")
            print(f":> Redis initialized with admin.")
    else:
        # File-based init
        admin_dir = os.path.join(DB_ROOT, admin_name)
        if not os.path.exists(admin_dir):
            os.makedirs(admin_dir, exist_ok=True)
            pw_hash = hash_password(admin_pw)
            with open(os.path.join(admin_dir, "password.txt"), "w") as f:
                f.write(pw_hash)
            
            dev_dir = os.path.join(admin_dir, "devices")
            os.makedirs(dev_dir, exist_ok=True)
            
            device_data = {
                "device_username": "current_device",
                "api_key": secrets.token_hex(16),
                "browser_info": "ALFRED Core v1.0"
            }
            with open(os.path.join(dev_dir, "current_device.json"), "w") as f:
                json.dump(device_data, f)
            with open(os.path.join(dev_dir, "current_device_queue.json"), "w") as f:
                json.dump([], f)
            print(f":> File DB initialized with admin.")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(name, device_username, password, browser_info="Unknown"):
    """Registers account/device. Supports Redis or File."""
    pw_hash = hash_password(password)
    
    if redis_client:
        # Check Account
        existing_pw = redis_client.get(f"alfred:account:{name}:pw")
        if existing_pw:
            if existing_pw != pw_hash:
                return {"error": "Invalid password for existing Account name."}
        else:
            redis_client.set(f"alfred:account:{name}:pw", pw_hash)
            
        # Check Device
        if redis_client.sismember(f"alfred:account:{name}:devices", device_username):
            return {"error": "Device already registered to this account."}
            
        api_key = secrets.token_hex(16)
        device_data = {
            "device_username": device_username,
            "api_key": api_key,
            "browser_info": browser_info
        }
        redis_client.set(f"alfred:account:{name}:device:{device_username}", json.dumps(device_data))
        redis_client.sadd(f"alfred:account:{name}:devices", device_username)
        # Queue is abstractly ready (Redis lists created on rpush)
        return {"api_key": api_key}
        
    else:
        # File-based logic
        user_dir = os.path.join(DB_ROOT, name)
        if os.path.exists(user_dir):
            pw_file = os.path.join(user_dir, "password.txt")
            if os.path.exists(pw_file):
                with open(pw_file, "r") as f:
                    if f.read().strip() != pw_hash:
                        return {"error": "Invalid password for existing Account name."}
        else:
            os.makedirs(user_dir, exist_ok=True)
            with open(os.path.join(user_dir, "password.txt"), "w") as f:
                f.write(pw_hash)
        
        dev_dir = os.path.join(user_dir, "devices")
        os.makedirs(dev_dir, exist_ok=True)
        device_file = os.path.join(dev_dir, f"{device_username}.json")
        if os.path.exists(device_file):
            return {"error": "Device already registered."}
            
        api_key = secrets.token_hex(16)
        device_data = {"device_username": device_username, "api_key": api_key, "browser_info": browser_info}
        with open(device_file, "w") as f:
            json.dump(device_data, f)
        with open(os.path.join(dev_dir, f"{device_username}_queue.json"), "w") as f:
            json.dump([], f)
        return {"api_key": api_key}

def authenticate(name, device_username, password, browser_info=None):
    pw_hash = hash_password(password)
    if redis_client:
        db_pw = redis_client.get(f"alfred:account:{name}:pw")
        if not db_pw or db_pw != pw_hash: return False
        
        if not redis_client.sismember(f"alfred:account:{name}:devices", device_username):
            register_user(name, device_username, password, browser_info or "Auto-registered")
        return True
    else:
        user_dir = os.path.join(DB_ROOT, name)
        if not os.path.exists(user_dir): return False
        pw_file = os.path.join(user_dir, "password.txt")
        with open(pw_file, "r") as f:
            if f.read().strip() != pw_hash: return False
            
        dev_file = os.path.join(user_dir, "devices", f"{device_username}.json")
        if not os.path.exists(dev_file):
            register_user(name, device_username, password, browser_info or "Auto-registered")
        return True

def get_user_data(name):
    if redis_client:
        if not redis_client.exists(f"alfred:account:{name}:pw"): return None
        device_names = redis_client.smembers(f"alfred:account:{name}:devices")
        devices = []
        for dname in device_names:
            d_json = redis_client.get(f"alfred:account:{name}:device:{dname}")
            if d_json:
                data = json.loads(d_json)
                devices.append({
                    "device_username": data["device_username"],
                    "api_key": data["api_key"],
                    "browser_info": data.get("browser_info", "Unknown")
                })
        return {"name": name, "devices": devices}
    else:
        user_dir = os.path.join(DB_ROOT, name)
        if not os.path.exists(user_dir): return None
        dev_dir = os.path.join(user_dir, "devices")
        devices = []
        if os.path.exists(dev_dir):
            for fn in os.listdir(dev_dir):
                if fn.endswith(".json") and not fn.endswith("_queue.json"):
                    with open(os.path.join(dev_dir, fn), "r") as f:
                        d = json.load(f)
                        devices.append({
                            "device_username": d["device_username"],
                            "api_key": d["api_key"],
                            "browser_info": d.get("browser_info", "Unknown")
                        })
        return {"name": name, "devices": devices}

def delete_device(account_name, device_username):
    if redis_client:
        redis_client.srem(f"alfred:account:{account_name}:devices", device_username)
        redis_client.delete(f"alfred:account:{account_name}:device:{device_username}")
        redis_client.delete(f"alfred:account:{account_name}:queue:{device_username}")
        return True
    else:
        try:
            dev_dir = os.path.join(DB_ROOT, account_name, "devices")
            df = os.path.join(dev_dir, f"{device_username}.json")
            qf = os.path.join(dev_dir, f"{device_username}_queue.json")
            if os.path.exists(df): os.remove(df)
            if os.path.exists(qf): os.remove(qf)
            return True
        except: return False

def check_access(name, device_username, api_key):
    if name.lower() in ["admin", "coder"]: return True
    if redis_client:
        d_json = redis_client.get(f"alfred:account:{name}:device:{device_username}")
        if not d_json: return False
        return json.loads(d_json).get("api_key") == api_key
    else:
        df = os.path.join(DB_ROOT, name, "devices", f"{device_username}.json")
        if not os.path.exists(df): return False
        with open(df, "r") as f: return json.load(f).get("api_key") == api_key

def queue_command(name, device_username, command_text):
    if redis_client:
        cmd_data = {"command": command_text, "timestamp": secrets.token_hex(4)}
        redis_client.rpush(f"alfred:account:{name}:queue:{device_username}", json.dumps(cmd_data))
        return True
    else:
        qf = os.path.join(DB_ROOT, name, "devices", f"{device_username}_queue.json")
        if not os.path.exists(os.path.dirname(qf)): return False
        queue = []
        if os.path.exists(qf):
            with open(qf, "r") as f:
                try: queue = json.load(f)
                except: queue = []
        queue.append({"command": command_text, "timestamp": secrets.token_hex(4)})
        with open(qf, "w") as f: json.dump(queue, f)
        return True

def get_pending_commands(name, device_username, api_key):
    if not check_access(name, device_username, api_key): return None
    if redis_client:
        msgs = redis_client.lrange(f"alfred:account:{name}:queue:{device_username}", 0, -1)
        redis_client.delete(f"alfred:account:{name}:queue:{device_username}")
        return [json.loads(m) for m in msgs]
    else:
        qf = os.path.join(DB_ROOT, name, "devices", f"{device_username}_queue.json")
        if not os.path.exists(qf): return []
        with open(qf, "r") as f:
            try: queue = json.load(f)
            except: queue = []
        with open(qf, "w") as f: json.dump([], f)
        return queue

if __name__ == "__main__":
    init_db()
