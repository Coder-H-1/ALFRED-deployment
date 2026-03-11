import time
import requests
import json
import traceback
import sys
import os

from FILES.commands import process_command
from FILES.utils import Responder, speak

# ---------------- CONFIGURATION ----------------
VERCEL_API_BASE = "https://project-alfred-custom-gpt.vercel.app/api"
POLL_INTERVAL_SECONDS = 2.0
# ------------------------------------------------

class GlobalCommandListener:
    def __init__(self, name, device_username, api_key):
        self.name = name
        self.device_username = device_username
        self.api_key = api_key
        self.poll_url = f"{VERCEL_API_BASE}/{self.name}/{self.device_username}/?api_key={self.api_key}"

    def start(self):
        print(f":> ALFRED Local Command Listener started.")
        print(f":> Linked to Vercel account: {self.name} | Device: {self.device_username}")
        print(f":> Polling Vercel every {POLL_INTERVAL_SECONDS} seconds...\n")
        
        while True:
            try:
                self.poll()
                time.sleep(POLL_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                print("\n:> Terminating listener.")
                break
            except Exception as e:
                print(f":> Polling error: {e}")
                time.sleep(POLL_INTERVAL_SECONDS * 2) # Backoff on error

    def poll(self):
        """Fetches pending commands from the Vercel cloud queue."""
        try:
            response = requests.get(self.poll_url, timeout=5)
            if response.status_code == 200:
                commands = response.json()
                if commands and isinstance(commands, list):
                    for command in commands:
                        self.execute_local(command)
            elif response.status_code == 401 or response.status_code == 403:
                print(f":> Access Denied by Vercel. Have you been disabled or used the wrong API key? (Status: {response.status_code})")
                time.sleep(10) # Heavy backoff on auth failure
        except requests.exceptions.RequestException:
            # Silent fail for network drops to avoid spamming the terminal
            pass

    def execute_local(self, command_text):
        """Executes the command on the Windows host machine."""
        print(f"\n[CLOUD RELAY] Received Command: '{command_text}'")
        try:
            # First, check if it's a known system command
            system_action = process_command(command_text)
            
            if system_action:
                speak(system_action)
            else:
                # If not a system command, pass to the LLM Responder
                response = Responder(command_text)
                speak(response) 
        except Exception as e:
            print(f":> Execution failed: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print("-" * 40)
    print("  A.L.F.R.E.D Global Command Listener  ")
    print("-" * 40)
    print("\nPlease enter your target Vercel credentials.")
    
    _name = input("Account Name: ").strip()
    _device = input("Device Username: ").strip()
    _api_key = input("API Key: ").strip()
    
    if not _name or not _device or not _api_key:
        print("Required fields missing. Exiting.")
        sys.exit(1)
        
    listener = GlobalCommandListener(_name, _device, _api_key)
    listener.start()
