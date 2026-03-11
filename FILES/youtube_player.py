# youtube_player.py

try:
    from FILES.util_functions import speak
except:
    from util_functions import speak     
player = None
VOLUME_youtube = 100

import threading
import subprocess   
import time
import vlc

def wait_until_finished(player):
    while True:
        state = player.get_state()
        if state in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
            break
        time.sleep(0.25)


def play_youtube_audio(query):
    global player

    speak("Let me fetch that, sir.")

    cmd = [
        "yt-dlp",
        f"ytsearch:{query}",
        "-f", "bestaudio",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-g"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # yt-dlp may print multiple lines; URL is usually the last valid one
        lines = result.stdout.strip().splitlines()
        audio_url = lines[-1]

        player = vlc.MediaPlayer(audio_url)
        if not player:
            print(":> [VLC ERROR] Failed to create MediaPlayer instance.")
            return "I'm sorry, sir. VLC player failed to initialize."
            
        player.audio_set_volume(VOLUME_youtube)
        player.play()
        print(f":> [VLC] Playback started for: {query}")
        time.sleep(5)

        threading.Thread(
            target=wait_until_finished,
            args=(player,),
            daemon=True
        ).start()

    except subprocess.CalledProcessError as e:
        print("[yt-dlp ERROR]", e.stderr)
        return "I'm sorry, I couldn't find that song, sir."
    except Exception as e:
        print(f":> [PLAYBACK CRITICAL] {e}")
        return f"An error occurred during playback: {str(e)}"
    
    return "Playing now, sir."


def stop_youtube_audio():
    global player
    if player:
        player.stop()
        return ("Stopped YouTube playback, sir.")
    else:
        return "Player not working, sir."
        

def set_volume_youtube():
    global player, VOLUME_youtube
    if player:
        player.audio_set_volume(VOLUME_youtube)