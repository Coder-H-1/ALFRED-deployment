

import keyboard
import subprocess
import threading
import time

from plyer import notification



notification.notify(
    title="ALFRED Activated",
    message="Working now.",
    app_name="Alfred.",
    timeout=5
    )




def wait_for_hotkey():
    while True:
        keyboard.wait("alt+shift+a+s")  
        time.sleep(0.1)  # Wait for sequential press
        if keyboard.is_pressed("d"):
            subprocess.Popen(['python', "main.py"])



if __name__ == "__main__":    
    threading.Thread(target=wait_for_hotkey, daemon=True).start()

    # Keeps launcher running forever
    while True:
        time.sleep(0.2)