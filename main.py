
from FILES.utils import Responder , get_greeting, MEMORY
from FILES.commands import process_command
from FILES.util_functions import listen_command, speak
from FILES.intent import INTENT
from FILES.backend.server import run_api
import os, sys, threading

COMMAND_INPUT = False

# Launch Background API on startup
threading.Thread(target=run_api, daemon=True).start()




def Command() -> str:
    if COMMAND_INPUT:
        command = str(input(">> ")).lower()
    
    else:
        command = listen_command()

    return command

def main():
    global COMMAND_INPUT
    speak("System is now fully operational.")
    os.system("title ALFRED")
    speak(get_greeting())
    Intent: object = INTENT()  

    while True:
        command = Command()
        if command==None: continue
        query_intent = Intent.get(command)

        if "switch command" in command:
            if COMMAND_INPUT:
                COMMAND_INPUT = False
            else:
                COMMAND_INPUT = True
                
            continue
        
        if "restart yourself" in command or "restart yourselves" in command or "restart your self" in command or "restart your" in command:
            os.startfile("Main.py")
            sys.exit()

        if "exit" in command or "goodbye" in command or "bye alfred" in command:
            MEMORY.session_end()
            speak(Responder("good day alfred. Now you may close yourself."))
            sys.exit()
            
        
        system_action = process_command(command, query_intent)
        if system_action:
            speak(system_action)
            MEMORY.add_to_history(command, system_action)
        else:
            response = Responder(command)
            speak(response) 


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error)
