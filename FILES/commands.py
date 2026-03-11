from FILES.util_functions import search_files
from FILES.utils import clear_Memory, get_date, get_time
from FILES.model_manager import ModelManager

from FILES.system_control import (
    mute_volume, 
    adjust_brightness,
    adjust_volume, 
    set_brightness,
    set_volume
)
from FILES.youtube_player import (
    play_youtube_audio, 
    stop_youtube_audio,
    set_volume_youtube
)

import keyboard
import os
import webbrowser

# Global for youtube volume (shared with youtube_player)
import FILES.youtube_player as yt_player

def handle_youtube_play(command: str):
    parts = command.split("play", 1)
    if len(parts) > 1:
        query = parts[1].replace("from youtube", "").replace("on youtube", "").strip()
        if query:
            play_youtube_audio(query)
            return "Done."
        return "Could you please repeat the song, sir?"
    return "Please specify what you'd like to play, sir."

def handle_youtube_volume(command: str):
    if "set" in command:
        for word in command.split():
            if word.isdigit():
                yt_player.VOLUME_YOUTUBE = int(word)
                set_volume_youtube()
                return f"Youtube's volume is now set to : {yt_player.VOLUME_YOUTUBE}%"
        return "Couldn't set volume. Could you please specify a number, sir?"

    if "increase" in command:
        yt_player.VOLUME_YOUTUBE += 10
        set_volume_youtube()
        return f"Youtube volume increased to : {yt_player.VOLUME_YOUTUBE}%"
    elif "decrease" in command:
        yt_player.VOLUME_YOUTUBE -= 10
        set_volume_youtube()
        return f"Youtube volume decreased to : {yt_player.VOLUME_YOUTUBE}%"
    return None

def handle_system_volume(command: str):
    if "mute" in command:
        return mute_volume()
    if "increase" in command:
        return adjust_volume("increase")
    if "decrease" in command:
        return adjust_volume("decrease")
    if "set" in command:
        for word in command.split():
            if word.isdigit():
                return set_volume(int(word))
    return None

def handle_brightness(command: str):
    if "increase" in command:
        return adjust_brightness("increase")
    if "decrease" in command:
        return adjust_brightness("decrease")
    if "set" in command:
        for word in command.split():
            if word.isdigit():
                return set_brightness(int(word))
    return None

def handle_search_file(command: str):
    parts = command.split("file", 1)
    if len(parts) > 1:
        query = parts[1].strip()
        return search_files(query)
    return "Might I ask which file you’re looking for, sir?"

# Application map for open/close commands
APPS = {
    "notepad": {"exe": "notepad.exe", "start": "start notepad"},
    "cmd": {"exe": "cmd.exe", "start": "start cmd"},
    "command prompt": {"exe": "cmd.exe", "start": "start cmd"},
    "task manager": {"exe": "taskmgr.exe", "shortcut": "ctrl+shift+esc"},
    "code": {"exe": "code.exe", "start": "code"},
    "chrome": {"exe": "chrome.exe", "start": "start chrome"},
    "firefox": {"exe": "firefox.exe", "start": "start firefox.exe"},
    "calculator": {"exe": "calc.exe", "start": "start calc"},
    "whatsapp": {"exe": "whatsapp.exe", "start": "start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"},
}

def handle_app_control(command: str):
    # Determine if it's open or close
    is_open = any(word in command for word in ["open", "start", "$"])
    is_close = any(word in command for word in ["close", "end", "&"])
    
    if not (is_open or is_close):
        return None

    for app_name, info in APPS.items():
        if app_name in command:
            if is_open:
                if "shortcut" in info:
                    keyboard.press_and_release(info["shortcut"])
                else:
                    os.system(info["start"])
                return f"Opening {app_name.capitalize()}, sir."
            else:
                os.system(f"taskkill /f /im {info['exe']}")
                return f"Closed {app_name.capitalize()}."
    return None

def process_command(command: str, Intent: str = None) -> str:
    """Modular command processor using a registry-like approach for expandability."""
    cmd = command.lower().strip()

    # 1. Youtube Controls
    if "youtube" in cmd and "volume" in cmd:
        return handle_youtube_volume(cmd)
    if "play" in cmd:
        return handle_youtube_play(cmd)
    if "stop youtube" in cmd or "stop music" in cmd:
        return stop_youtube_audio()

    # 2. System Controls
    if "volume" in cmd:
        return handle_system_volume(cmd)
    if "brightness" in cmd:
        return handle_brightness(cmd)
    
    # 3. Time/Date
    if "time" in cmd and "what" in cmd:
        return get_time()
    if ("date" in cmd or "day" in cmd) and "what" in cmd:
        return get_date()

    # 4. App Controls (Modular)
    app_res = handle_app_control(cmd)
    if app_res: return app_res

    # 5. System Utilities
    if "clear screen" in cmd or "clear terminal" in cmd:
        os.system("cls")
        return "Cleared the screen, sir."
    if "go to desktop" in cmd or "main screen" in cmd:
        keyboard.press_and_release("win + d")
        return "You are on the desktop now."
    if "shutdown" in cmd:
        os.system("shutdown /s /t 1")
        return "Shutting down the system now."
    if "restart computer" in cmd or "restart system" in cmd:
        os.system("shutdown /r /t 1")
        return "Restarting your machine, sir."
    
    # 6. Memory/Search
    if "clear memory" in cmd or "forget everything" in cmd:
        clear_Memory()
        return "I have cleared my memory as you requested."
    if "search file" in cmd or "find file" in cmd:
        return handle_search_file(cmd)

    return None




