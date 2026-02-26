#py -m pip install --upgrade pip
#py -m pip install keyboard
#py -m pip install python-telegram-bot
import time
import keyboard
from telegram import Bot
import requests

def sendTelegramMessage(message):
    TOKEN = "1809194206:AAFihMqNhJvYADML-2Y7p71L8kVrKLYQalw"
    chat_id = "1398799702"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
    print(requests.get(url).json())  # this sends the message
   



start_time = 0
is_running = False

def on_key_event(e):
    global start_time
    global is_running

    if e.event_type == keyboard.KEY_DOWN:
        if e.name == 'a':
            start_time = time.time()
            is_running = True
            print("Stopwatch started/restarted.")

        elif e.name == 'q' and is_running:
            end_time = time.time()
            elapsed_time_ms = (end_time - start_time) * 1000
            is_running = False
            sendTelegramMessage(f"Elapsed time: {elapsed_time_ms:.2f} milli seconds")
            print(f"Elapsed time: {elapsed_time_ms:.2f} milli seconds")
            print("Stopwatch stopped.")

keyboard.hook(on_key_event)

try:
    keyboard.wait('esc')  # Wait for the 'esc' key to exit the script
except KeyboardInterrupt:
    pass
finally:
    keyboard.unhook_all()