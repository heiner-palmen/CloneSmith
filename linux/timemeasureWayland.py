#!/usr/bin/env python3
# <Waybind> Copyright (C) 2025 JJ Posti (techtimejourney.net)
# GPL Version 2 License
import os
import sys
import yaml
import time
import threading
import subprocess
import getpass
from telegram import Bot
import requests
from evdev import InputDevice, categorize, ecodes, list_devices
import json

# Config: token/chat id may be provided via JSON config file in the same directory
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'timemeasure_config.json')

# Allow overrides from environment variables
TOKEN = os.environ.get('TIMEMEASURE_TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TIMEMEASURE_TELEGRAM_CHAT_ID')


def load_config():
    """Load TOKEN and CHAT_ID from CONFIG_FILE if present.
    Environment variables take precedence.
    """
    global TOKEN, CHAT_ID
    try:
        with open(CONFIG_FILE, 'r') as fh:
            cfg = json.load(fh)
        if not TOKEN:
            TOKEN = cfg.get('token') or cfg.get('TOKEN')
        if not CHAT_ID:
            CHAT_ID = cfg.get('chat_id') or cfg.get('CHAT_ID')
    except FileNotFoundError:
        # no config file — that's fine
        return
    except Exception as e:
        print(f"Failed to load config {CONFIG_FILE}: {e}")


load_config()


MODIFIER_KEYS = {
    ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL,
    ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT,
    ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA
}

MODIFIER_NAMES = {
    ecodes.KEY_LEFTCTRL: "CTRL", ecodes.KEY_RIGHTCTRL: "CTRL",
    ecodes.KEY_LEFTALT: "ALT", ecodes.KEY_RIGHTALT: "ALT",
    ecodes.KEY_LEFTMETA: "SUPER", ecodes.KEY_RIGHTMETA: "SUPER"
}

stopwatch_running = False
start_time = None


def sendTelegramMessage(message):
    if not TOKEN or not CHAT_ID:
        print('sendTelegramMessage: TOKEN or CHAT_ID not configured; skipping')
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        print(requests.get(url).json())  # this sends the message
    except Exception as e:
        print('sendTelegramMessage: request failed:', e)


def is_keyboard_device(dev):
    try:
        if "keyboard" in dev.name.lower():
            return True
        keys = dev.capabilities().get(ecodes.EV_KEY, [])
        return ecodes.KEY_A in keys and ecodes.KEY_ENTER in keys
    except Exception:
        return False


def find_keyboard_devices():
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if is_keyboard_device(dev):
                devices.append(path)
        except Exception:
            continue
    return devices


def keycode_to_name(code):
    if code in MODIFIER_NAMES:
        return MODIFIER_NAMES[code]
    try:
        return ecodes.KEY[code].replace("KEY_", "").upper()
    except KeyError:
        return None


def read_keyboard_events(path):
    global stopwatch_running, start_time
    try:
        dev = InputDevice(path)
    except Exception as e:
        print(f"Failed to open device {path}: {e}")
        return

    pressed = set()
    for event in dev.read_loop():
        if event.type != ecodes.EV_KEY:
            continue

        e = categorize(event)
        if e.keystate == e.key_down:
            pressed.add(e.scancode)
        elif e.keystate == e.key_up:
            pressed.discard(e.scancode)

        names = [keycode_to_name(c) for c in pressed]
        combo = tuple(sorted(filter(None, names)))

        if e.keystate == e.key_down:
            key_name = keycode_to_name(e.scancode)
            if key_name == 'A':
                # Start or restart stopwatch
                start_time = time.time()
                stopwatch_running = True
                print("Stopwatch started or restarted.")
            elif key_name == 'Q' and stopwatch_running:
                elapsed_time_ms = (time.time() - start_time) * 1000
                print(f"Elapsed time: {elapsed_time_ms:.2f} milli seconds")
                print("Stopwatch stopped.")
                sendTelegramMessage(f"Elapsed time: {elapsed_time_ms:.2f} milli seconds")
                stopwatch_running = False
            else:
                print(f"key pressed: {key_name}")


def run_service():
   
    devices = find_keyboard_devices()
    if not devices:
        print("No keyboard devices found. Ensure you have permission to access /dev/input.")
        return

    for path in devices:
        threading.Thread(
            target=read_keyboard_events,
            args=(path,),
            daemon=True
        ).start()

    # Do not block the terminal — just keep running quietly
    print("Waybind started.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Waybind stopped.")


if __name__ == "__main__":
    run_service()

