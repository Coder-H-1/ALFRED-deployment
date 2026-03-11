########################################################################################################################################
### > Internet ###
import requests

def get_Data_state() -> bool:  ###  Checks internet state
    "Checks if internet is connected or not -> returns True/False"

    try:
        requests.get(f"https://www.google.com", timeout=2) # Added timeout
        return True
    except:
        return False

########################################################################################################################################
### > Text editing ###

def EDIT(text: str, FROM_str: list, TO_str: list = None) -> str:
    """Refactored EDIT: A lightweight wrapper for standard string replacement."""
    text = str(text).lower()
    for i, old in enumerate(FROM_str):
        new = TO_str[i] if TO_str and i < len(TO_str) else (TO_str[0] if TO_str else "")
        text = text.replace(str(old).lower(), str(new))
    return text

def Text_Editor(text: str, FROM_str: list, TO_str: list = None) -> str:
    """Alias for EDIT for backward compatibility."""
    return EDIT(text, FROM_str, TO_str)

class _EditWrapper:
    """Minimal class wrapper for code expecting EDIT(text, ...).replace_to_none()"""
    def __init__(self, text, FROM_str, TO_str=None):
        self.text = text
        self.FROM_str = FROM_str
        self.TO_str = TO_str
    def replace_to_none(self):
        return EDIT(self.text, self.FROM_str, None)
    def replace(self):
        return EDIT(self.text, self.FROM_str, self.TO_str)

# Re-expose as a class-like factory for backward compatibility
def LegacyEDIT(text, FROM_str, TO_str=None):
    return _EditWrapper(text, FROM_str, TO_str)

#########################################################################################################################################

### Speech ###

import queue
import threading
import os
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

_speech_queue = queue.Queue()

def _speaker_worker():
    """Dedicated thread for speaking to avoid COM/threading issues."""
    try:
        if not HAS_PYTTSX3:
            return
        
        engine = pyttsx3.init("sapi5")
        engine.setProperty("rate", 170)
        voices = engine.getProperty("voices")
        if len(voices) >= 3:
            engine.setProperty("voice", voices[3].id)
        
        while True:
            t = _speech_queue.get()
            if t is None: break
            engine.say(t)
            engine.runAndWait()
            _speech_queue.task_done()
    except Exception as e:
        print(f":> [SPEECH ERROR] {e}")

# Start the background speaker thread only if we have TTS capabilities
if HAS_PYTTSX3 and not os.environ.get("VERCEL"):
    threading.Thread(target=_speaker_worker, daemon=True).start()

def speak(text: str = None, speech_rate: int = 170) -> None:  ### Speaks the text given
    "Text to Speech function"
    if text is None: return

    if "sir" not in text.lower():
        text = f"{text.rstrip('.')}, sir."

    print(f"Alfred: {text}")
    _speech_queue.put(text)

######################################################################################################################
### > Speech Recognition

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False

# listen_commands configuration
if HAS_SR:
    RECOGNIZER = sr.Recognizer()
    MIC = sr.Microphone()
else:
    RECOGNIZER = None
    MIC = None
    

def listen_command() -> str:   ### Listens the user speech using speech_recognition
    if not HAS_SR:
        return None
        
    r = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            print(":> Listening...")
            audio = r.listen(source) 

        try:
            print("Recognizing...")
            query = r.recognize_google(audio, language="en-IN")  ## Uses online google voice recognition system for Speech to Text
            if query:
                print(f"User said : {query}")
                return str(query).lower()
        except:
            return None

######################################################################################################################
### SEARCH FILES 
import os

EXCLUDED_DIRS = {
    "C:\\Windows", 
    "C:\\Program Files", 
    "C:\\Program Files (x86)", 
    "C:\\$Recycle.Bin", 
    "System Volume Information",
    ".git",
    "__pycache__",
    "node_modules"
}

def search_files(filename: str, search_path="C:\\", is_commanded:bool=False, to_find:int=5) -> str:
    "Optimized file search that avoids system directories and excessive printing"
    results = []
    query = filename.lower()

    if not is_commanded: 
        speak("Allow me a moment while I search for your file, sir.")

    try:
        for root, dirs, files in os.walk(search_path):
            # Prune excluded directories to speed up traversal
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in EXCLUDED_DIRS and d not in EXCLUDED_DIRS]
            
            for file in files:
                if query in file.lower():
                    results.append(os.path.join(root, file))
                    if len(results) >= to_find:
                        break
            if len(results) >= to_find:
                break
    except Exception as e:
        print(f"Search error: {e}")

    if results:
        if is_commanded:
            return results[0] # Return the first match for automated commands
        else:    
            speak("I found some matches, sir. Here they are:")
            for idx, path in enumerate(results, 1):
                print(f"{idx}. 📁 {path}")

            speak("Shall I open the first result for you?")
            confirmation = listen_command()

            if confirmation and ("yes" in confirmation or "open" in confirmation):
                try:
                    os.startfile(results[0])
                    return "Opening the file now."
                except Exception as e:
                    return f"I'm afraid I couldn’t open it. The error was: {e}"

            return "Very well, I shall await further instructions."
    else:
        return "I'm afraid I found no matching files, sir."

######################################################################################################################
### Memory Container
try:
    from FILES.memory import Memory
except:    
    from memory import Memory
MEMORY = Memory()

