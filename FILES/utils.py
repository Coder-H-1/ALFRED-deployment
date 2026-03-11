"""
`utils.py` loads the Large Language Model (LLM)

Functions:
    get_time() -> str
    get_date() -> str
    get_greeting() -> str
    clear_Memory() -> None
    Response(query: str) -> str

    Note : 'query' is the input given by the user (either through voice input or from text input)

Working:
    It creates an object called `MEMORY` -> Controls and recalls chat history

    It creates another object called `LLM` -> load LLaMa model 
                :-> n_ctx       = 2048        (tokens input)
                :-> max_token   = 100         (token output per prompt)

    
"""

import os
import datetime
import random
import threading

VERCEL = os.environ.get("VERCEL")

try: 
    if VERCEL:
        raise ImportError("Skipping LLAMA on Vercel")
    from llama_cpp import Llama
    HAS_LLAMA = True
except (ModuleNotFoundError, ImportError): 
    HAS_LLAMA = False

try: 
    from FILES.util_functions import Text_Editor, Memory, MEMORY
except (ModuleNotFoundError, ImportError): 
    try:
        from util_functions import Text_Editor, Memory, MEMORY
    except (ModuleNotFoundError, ImportError):
        # Fallback for direct script execution if needed
        import sys
        sys.path.append(os.path.dirname(__file__))
        from util_functions import Text_Editor, Memory, MEMORY


def get_time() -> str: ## Checks Time > returns a string ("It is %I:%M %p, sir")
    now = datetime.datetime.now()
    return now.strftime("It is %I:%M %p, sir.")  # 12-hour format

def get_date() -> str:  ## Checks Date > returns a string ("Today is %A, %d %B %Y.") 
    today = datetime.datetime.now()
    return today.strftime("Today is %A, %d %B %Y.")

def get_greeting() -> str: ## Greets user
    hour = datetime.datetime.now().hour

    _time = get_time().replace("It is ", "The time is ").replace(", sir." , "")
    _date = get_date().replace("." , " ")
    Time_and_Date = f"{_date} and {_time}"
    if 5 <= hour < 12:
        greet = f"Good morning, sir."
    elif 12 <= hour < 17:
        greet = f"Good afternoon, sir."
    elif 17 <= hour < 21:
        greet = f"Good evening, sir."
    else:
        greet = "Working late are we sir."
    
    MEMORY.add_to_history(Time_and_Date, greet)
    return greet
    
def clear_Memory() -> None: MEMORY.clean_history()  # Clears all the previous Session chat history

# FOR LLM

def get_optimal_threads(reserve=2) -> int: ## For CPU usage control  > reserves atleast 2 cpu cores for Operating System 
    total:int = os.cpu_count() or 4
    threads:int = max(1, total - reserve)
    print(f":> Using {threads} threads out of {total} logical cores.")
    return int(threads)

MODEL_PATH:str = "FILES\\model\\model3.gguf"  
   
_LLM_INSTANCE = None
_LLM_READY = threading.Event()

def _load_model_thread():
    """Background task to initialize the model."""
    global _LLM_INSTANCE
    if not HAS_LLAMA:
        _LLM_READY.set()
        return

    try:
        print(":> System warming up (Loading LLM in background)...")
        _LLM_INSTANCE = Llama(
            model_path=MODEL_PATH,
            n_ctx=512, # Reduced to 512 for memory efficiency
            n_threads=get_optimal_threads(),
            verbose=False 
        )
        _LLM_READY.set()
        print(":> System Ready (LLM Loaded).")
    except Exception as e:
        print(f":> Error loading LLM: {e}")
        _LLM_READY.set()

# Start pre-loading immediately on import
if not VERCEL:
    threading.Thread(target=_load_model_thread, daemon=True).start()
else:
    _LLM_READY.set()

def get_llm():
    """Returns the LLM instance, waiting if it's still loading."""
    if not HAS_LLAMA:
        return None
    if not _LLM_READY.wait(timeout=60): # Wait up to 30 seconds
        print(":> Warning: LLM loading is taking longer than expected.")
    return _LLM_INSTANCE

def Responder(prompt: str) -> str: ### Reponds user query
    "Reponds user query using Chat Model"

    MEMORY.remember("last_command", prompt) 
    ### sets key = "last_command" to value = (prompt)
    
    if not HAS_LLAMA:
        answer = "I'm sorry, sir. My core AI engine is currently disabled in the serverless environment."
        MEMORY.add_to_history(prompt, answer)
        return answer

    llm = get_llm()
    if llm is None:
        return "I'm sorry, sir. The model failed to load. Please check if the model file exists."

    history: str = MEMORY.get_history()   ## Chat History
     
    inject: str = (  ### Prompt 
        "Full Name : Automated Limited Functionality Responsive Educational Development (system). or ALFRED.\n"
        "Work : Reply with polite, relevant and brief answers.\n"
        "Functionality : ALFRED is programmed with multiple assistance systems including text generation, open-closing applications and many more.\n "
        f"{history}\n"
        f"User said: {prompt}\nALFRED: "
    )

    out: object = llm(inject , max_tokens = 150, stop=["User:", "ALFRED:"], echo=False)  
    ### Prompts the LLM model and expects a reply    
    ### max_tokens = length of responce ; here 150 = words/tokens

    # Default to the first choice if available
    choices = out.get("choices", [])
    if not choices:
        return "I'm sorry, I couldn't generate a response."
    
    answer: str = choices[0]["text"].strip()  
    
    if "User said" in answer:
        answer = answer.split("User said")[0].strip()

    # Clean up prefixes
    for prefix in ["Assistant:", "ALFRED:"]:
        if answer.lower().startswith(prefix.lower()):
            answer = answer[len(prefix):].strip()
    
    MEMORY.add_to_history(prompt, answer)
    return answer


# if __name__ == "__main__":   # to debug changes made in file

#     while True:
#         text:str = str(input(">> ")).strip()
#         print(Responder(text))
