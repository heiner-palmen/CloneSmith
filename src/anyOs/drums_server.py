import socket
import threading
import time
import os
import sys
import logging
import json
import requests

# cross-platform input helper: prefer evdev on Linux (non-root if /dev/uinput is group-writable),
# otherwise fall back to the `keyboard` library (works well on Windows).
USE_EVDEV = False
evdev_ui = None
evdev_ecodes = None
try:
    if sys.platform.startswith('linux') and os.path.exists('/dev/uinput') and os.access('/dev/uinput', os.W_OK):
        from evdev import UInput, ecodes as e
        evdev_ecodes = e
        evdev_ui = UInput()
        USE_EVDEV = True
except Exception:
    # evdev not available or not writable; we'll fall back to `keyboard` when needed
    evdev_ui = None
    evdev_ecodes = None

try:
    import keyboard
except Exception:
    keyboard = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timemeasure / stopwatch: listen for physical keyboard events (A to start/restart,
# Q to stop and send elapsed time via Telegram). This runs only when evdev is
# available for reading input devices.

# Config path: timemeasure_config.json next to this script (template:
# example_timemeasure_config.json; git-ignored, it holds the Telegram token).
# ../linux/ is the folder's old name, still read as a fallback.
_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_CANDIDATES = [
    os.path.join(_HERE, 'timemeasure_config.json'),
    os.path.normpath(os.path.join(_HERE, '..', 'linux', 'timemeasure_config.json')),
]
CONFIG_FILE = CONFIG_CANDIDATES[0]
# TOKEN/CHAT_ID are loaded from the config file only
TOKEN = None
CHAT_ID = None


def load_timemeasure_config():
    global TOKEN, CHAT_ID, CONFIG_FILE
    for candidate in CONFIG_CANDIDATES:
        if os.path.isfile(candidate):
            CONFIG_FILE = candidate
            break
    else:
        # used to fail silently: the stopwatch then never reached Telegram
        logger.warning('No timemeasure config found (%s); elapsed times are not sent to Telegram. '
                       'Copy example_timemeasure_config.json to %s',
                       ' or '.join(CONFIG_CANDIDATES), CONFIG_CANDIDATES[0])
        return
    try:
        with open(CONFIG_FILE, 'r') as fh:
            cfg = json.load(fh)
        if not TOKEN:
            TOKEN = cfg.get('token') or cfg.get('TOKEN')
        if not CHAT_ID:
            CHAT_ID = cfg.get('chat_id') or cfg.get('CHAT_ID')
        logger.info('Timemeasure config loaded from %s', CONFIG_FILE)
    except Exception as e:
        logger.warning('Failed to load timemeasure config %s: %s', CONFIG_FILE, e)


load_timemeasure_config()

# stopwatch state
stopwatch_running = False
stopwatch_start = None


def start_stopwatch():
    global stopwatch_running, stopwatch_start
    stopwatch_start = time.time()
    stopwatch_running = True
    logger.info('Stopwatch started/restarted')
    print("DEBUG: Stopwatch started/restarted")


def stop_stopwatch():
    global stopwatch_running, stopwatch_start
    if not stopwatch_running:
        return
    elapsed_ms = (time.time() - stopwatch_start) * 1000.0
    logger.info('Stopwatch stopped: %.2f ms', elapsed_ms)
    send_telegram_message(f'Elapsed time: {elapsed_ms:.2f} milli seconds')
    stopwatch_running = False
    print(f"DEBUG: Stopwatch stopped, elapsed: {elapsed_ms:.2f} ms")


def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        logger.info('send_telegram_message: TOKEN/CHAT_ID not configured; skipping')
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        resp = requests.get(url, timeout=5)
        logger.debug('Telegram response: %s', resp.text)
    except Exception as e:
        logger.warning('Failed to send Telegram message: %s', e)


# Try to import evdev readers for listening to /dev/input devices
EVDEV_READ_AVAILABLE = False
try:
    from evdev import InputDevice, categorize, ecodes as read_ecodes, list_devices
    EVDEV_READ_AVAILABLE = True
except Exception:
    EVDEV_READ_AVAILABLE = False


def find_keyboard_devices():
    if not EVDEV_READ_AVAILABLE:
        return []
    devices = []
    print("DEBUG: Searching for keyboard devices")
    for path in list_devices():
        try:
            dev = InputDevice(path)
            name = (dev.name or '').lower()
            if 'keyboard' in name:
                devices.append(path)
                print(f"DEBUG: Added keyboard device (name): {path}")
                continue
            caps = dev.capabilities().get(read_ecodes.EV_KEY, [])
            if read_ecodes.KEY_A in caps and read_ecodes.KEY_ENTER in caps:
                devices.append(path)
        except Exception:
            continue
    return devices


def read_keyboard_events(path):
    global stopwatch_running, stopwatch_start
    try:
        dev = InputDevice(path)
        print(f"DEBUG: Opened device {path} for reading")
    except Exception as e:
        logger.warning('Failed to open device %s: %s', path, e)
        return

    for event in dev.read_loop():
        if event.type != read_ecodes.EV_KEY:
            continue
        ev = categorize(event)
        if ev.keystate != ev.key_down:
            continue
        key_name = None
        try:
            key_name = read_ecodes.KEY[event.code].replace('KEY_', '').upper()
        except Exception:
            key_name = None
        print(f"DEBUG: Key pressed: {key_name} (code: {event.code})")
        if key_name == 'A':
            stopwatch_start = time.time()
            stopwatch_running = True
            logger.info('Stopwatch started/restarted')
            print("DEBUG: Stopwatch started/restarted")
        elif key_name == 'Q' and stopwatch_running:
            elapsed_ms = (time.time() - stopwatch_start) * 1000.0
            logger.info('Stopwatch stopped: %.2f ms', elapsed_ms)
            send_telegram_message(f'Elapsed time: {elapsed_ms:.2f} milli seconds')
            stopwatch_running = False
            print(f"DEBUG: Stopwatch stopped, elapsed: {elapsed_ms:.2f} ms")
        else:
            logger.debug('key pressed (monitor): %s', key_name)


def start_keyboard_listeners():
    if EVDEV_READ_AVAILABLE:
        devices = find_keyboard_devices()
        print(f"DEBUG: Found keyboard devices: {devices}")
        if not devices:
            logger.info('No keyboard input devices found')
            return
        for path in devices:
            threading.Thread(target=read_keyboard_events, args=(path,), daemon=True).start()
        logger.info('Keyboard listeners started for timemeasure using evdev')
        print("DEBUG: Using evdev for listening")
        return
    if keyboard is not None:
        keyboard.on_press_key('a', lambda _: start_stopwatch())
        keyboard.on_press_key('q', lambda _: stop_stopwatch())
        logger.info('Keyboard listeners started for timemeasure using keyboard module')
        print("DEBUG: Using keyboard module for listening")
        return
    logger.info('No input backend available for keyboard listening')



def _evdev_press(code, delay=0.05):
    # write press and release
    evdev_ui.write(evdev_ecodes.EV_KEY, code, 1)
    evdev_ui.write(evdev_ecodes.EV_KEY, code, 0)
    evdev_ui.syn()
    time.sleep(delay)


def send_key(name):
    """Send a single key by name. On Linux prefer evdev; on Windows use keyboard."""
    name = name.lower()
    if USE_EVDEV and evdev_ui is not None:
        # map common names to evdev codes
        mapping = {
            'enter': evdev_ecodes.KEY_ENTER,
            'esc': evdev_ecodes.KEY_ESC,
            'up': evdev_ecodes.KEY_UP,
            'down': evdev_ecodes.KEY_DOWN,
            'left': evdev_ecodes.KEY_LEFT,
            'right': evdev_ecodes.KEY_RIGHT,
            'a': evdev_ecodes.KEY_A,
            's': evdev_ecodes.KEY_S,
            'l': evdev_ecodes.KEY_L,
        }
        code = mapping.get(name)
        if code is None:
            logger.warning('send_key: unknown evdev key name: %s', name)
            return
        _evdev_press(code)
    else:
        if keyboard is None:
            logger.error('No input backend available: evdev not usable and keyboard module not installed')
            return
        keyboard.press_and_release(name)


def send_sequence(names, delays=None):
    for i, nm in enumerate(names):
        send_key(nm)
        if delays and i < len(delays):
            time.sleep(delays[i])


# --- Navigation helpers requested by user ---
def send_text(text, char_delay=0.1):
    """Type arbitrary text. Use evdev when available, otherwise keyboard.write."""
    if USE_EVDEV and evdev_ui is not None:
        for ch in text:
            # letters/digits/spaces
            if ch == ' ':
                code = getattr(evdev_ecodes, 'KEY_SPACE', None)
            else:
                name = f'KEY_{ch.upper()}'
                code = getattr(evdev_ecodes, name, None)
            if code is None:
                logger.warning('send_text: cannot map character %r to evdev, skipping', ch)
                continue
            _evdev_press(code, delay=char_delay)
    else:
        if keyboard is None:
            logger.error('send_text: no input backend available to type text')
            return
        keyboard.write(text)


def load_song_search():
    """chkit's song search (https://github.com/heiner-palmen/chkit): it reads
    the Clone Hero window and sends each key only where the screen shows it
    means what it should. Found installed (requirements.txt), via CHKIT_PATH,
    or as the chkit submodule next to CloneSmith in the failfloozie superrepo.
    None if it is not there or cannot run here (it needs Linux/X11 and evdev)."""
    candidates = [os.environ.get('CHKIT_PATH'),
                  os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'chkit'))]
    for folder in [None] + candidates:
        if folder:
            if not os.path.isfile(os.path.join(folder, 'chkit', '__init__.py')):
                continue
            sys.path.insert(0, folder)
        try:
            from chkit.game import search
            return search
        except ImportError as exc:
            if folder:
                logger.warning('chkit found at %s but not usable: %s', folder, exc)
    return None


def search_artist(artist):
    """Search request from the guitar client: the cursor of the song list on
    the first song of `artist`. Nothing is typed blindly: when the game window
    cannot be read, a song is running or a step does not show up on the
    screen, the search stops and the guitarist gets the reason.
    Returns the answer for the client: "OK" or "FAILED: <reason>"."""
    artist = (artist or '').strip()
    if not artist:
        return 'FAILED: nothing to search for'
    search = load_song_search()
    if search is None:
        return 'FAILED: chkit is missing (pip install git+https://github.com/heiner-palmen/chkit.git)'
    try:
        failed = search.find_artist(artist, log=logger.info)
    except Exception as exc:              # e.g. no access to /dev/uinput
        failed = f'{type(exc).__name__}: {exc}'
    return 'OK' if failed is None else f'FAILED: {failed}'


def in_song_to_mainscreen():
    # enter up 2x a 2x
    send_key('enter')
    time.sleep(0.5)
    send_key('up')
    time.sleep(0.3)
    send_key('a')
    time.sleep(0.3)
    send_key('a')


def mainscreen_to_ready_trigger():
    # 2x a
    send_key('a')
    time.sleep(0.3)
    send_key('a')


def handle_client(client_socket):
    request = client_socket.recv(1024)
    action = request.decode('utf-8')
    print(f"Received action: {action}")

    # allow optional payload after action, e.g. "Search some text"
    parts = action.strip().split(None, 1)
    cmd = parts[0]
    payload = parts[1] if len(parts) > 1 else None

    if cmd == "Trigger":
        print("Performing Trigger")
        send_key('a')
        client_socket.send(b"OK")

    elif cmd == "CancelSongToReady4Trigger":
        print("Performing CancelSongToReady4Trigger")
        in_song_to_mainscreen()
        time.sleep(3)
        mainscreen_to_ready_trigger()


    elif cmd == "Search":
        # screen-checked, never blind (the guitarist keeps control); the answer
        # says whether it went through or why not
        print("Performing Search")
        reply = search_artist(payload)
        print(f"Search: {reply}")
        client_socket.send(reply.encode('utf-8'))
    else:
        print("Unknown action:", action)
        client_socket.send(b"UNKNOWN")

    client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 12345))  # Change IP and port as needed
    server.listen(5)
    # start keyboard listeners for timemeasure stopwatch
    start_keyboard_listeners()

    # small test press on startup to ensure input backend is available
    print("Server listening on port 12345...")

    while True:
        client, addr = server.accept()
        print(f"Accepted connection from {addr[0]}:{addr[1]}")

        client_handler = threading.Thread(target=handle_client, args=(client,))
        client_handler.start()

if __name__ == "__main__":
    start_server()