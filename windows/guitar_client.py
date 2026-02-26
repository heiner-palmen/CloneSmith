import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import json
import os
import keyboard
import time
import threading
import socket

# Prefer a config next to this script; fall back to the repository root
config_candidates = [
    os.path.join(os.path.dirname(__file__), 'guitar_client_config.json'),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'guitar_client_config.json')),
]
drum_server = ''
static_offset = 0
for config_path in config_candidates:
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as cfg_file:
                _cfg = json.load(cfg_file)
            drum_server = str(_cfg.get('server', '') or '').strip()
            static_offset = int(_cfg.get('static_offset', 0) or 0)
            print(f"Loaded config from: {config_path}")
            break
    except Exception as e:
        # continue to next candidate
        print(f"Failed to load config {config_path}: {e}")

# Time-measure state (integrated from time_measure.py)
time_measure_hook = None
tm_start_time = None
tm_elapsed_ms = 0


def send_drum_start_trigger():
    send_to_drum("Trigger")


def send_drum_pause_trigger():
    send_to_drum("CancelSongToReady4Trigger")


def send_search_to_drum(search_text):
    """Send a Search command to the drum server with the given payload text."""
    payload = f"Search {search_text}"
    send_to_drum(payload)


def send_to_drum(message, timeout=5):
    """Send a raw message to the configured drum server using create_connection.

    This handles DNS resolution, IPv4/IPv6 selection, and reports clear errors.
    """
    if not drum_server:
        update_output("Drum server not configured (empty 'server' in guitar_client_config.json).")
        return
    try:
        # create_connection handles getaddrinfo and tries all returned addresses
        with socket.create_connection((drum_server, 12345), timeout=timeout) as client:
            client.send(message.encode('utf-8'))
        update_output(f"Sent to drum server: {message}")
    except OSError as ose:
        update_output(f"Network error sending to drum server ({drum_server}): {ose}")
    except Exception as e:
        update_output(f"Failed to send to drum server ({drum_server}): {e}")


def _time_key_event(event):
    """Keyboard hook handler for time measurement keys ('a' or 'enter')."""
    global tm_start_time, tm_elapsed_ms
    try:
        if event.event_type == 'down' and (event.name == 'a' or event.name == 'enter'):
            if tm_start_time is None:
                tm_start_time = time.time()
                update_output("Time measure started.")
            else:
                tm_elapsed_ms = int((time.time() - tm_start_time) * 1000)
                update_output(f"Time measure stopped. Elapsed time: {tm_elapsed_ms} ms")
                tm_start_time = None
    except Exception:
        pass


def enable_time_measure(enable):
    """Enable or disable the global keyboard time measurement hook."""
    global time_measure_hook
    if enable:
        if time_measure_hook is None:
            try:
                time_measure_hook = keyboard.hook(_time_key_event)
                update_output("Time measure enabled (press 'a' or Enter to measure).")
            except Exception as e:
                update_output(f"Failed to enable time measurement: {e}")
    else:
        if time_measure_hook is not None:
            try:
                keyboard.unhook(time_measure_hook)
            except Exception:
                try:
                    keyboard.unhook_all()
                except Exception:
                    pass
            time_measure_hook = None
            update_output("Time measure disabled.")


def on_combobox_change(event):
    selected_song_id = combobox.get()
    selected_song = songs.get(selected_song_id, {"offset": 0})
    offset_var.set(selected_song["offset"])
    update_output(f"Selected Song ID: {selected_song_id}, Offset: {offset_var.get()}")
    save_last_selected_song(selected_song_id)


def update_output(message):
    output_text.insert(tk.END, f"{message}\n")
    output_text.see(tk.END)


def clear_output():
    output_text.delete(1.0, tk.END)


def on_key_press_F1(event):
    # Apply stored per-song offset plus the static communication offset when triggering playback
    milliseconds = offset_var.get() + static_offset
    update_output(f"Applying static offset: {static_offset} ms")
    play_songs(milliseconds)


def on_key_press_F2(event):
    update_output(f"Trigger pause drums")
    milliseconds = offset_var.get()
    send_drum_pause_trigger()


def play_guitar():
    keyboard.press_and_release('enter')


def play_drums():
    send_drum_start_trigger()


def play_songs(milliseconds):
    if milliseconds < 0:
        update_output(f"Trigger start guitar")
        play_guitar()
        update_output(f"Waiting... Offset: {milliseconds}")
        time.sleep(abs(milliseconds) / 1000)
        update_output(f"Trigger start drums")
        play_drums()
    else:
        update_output(f"Trigger start drums")
        play_drums()
        update_output(f"Waiting... Offset: {milliseconds}")
        time.sleep(milliseconds / 1000)
        update_output(f"Trigger start guitar")
        play_guitar()


def load_songs():
    try:
        with open("songs.json", "r", encoding='utf-8') as file:
            songs_data = json.load(file)
        return songs_data
    except FileNotFoundError:
        print("Error: songs.json not found.")
        return {}


def save_last_selected_song(song_id):
    with open("last_selected_song.txt", "w", encoding='utf-8') as file:
        file.write(song_id)


def load_last_selected_song():
    try:
        with open("last_selected_song.txt", "r", encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None


def reload_json():
    global songs
    songs = load_songs()
    combobox['values'] = list(songs.keys())
    last_selected_song = load_last_selected_song()
    if last_selected_song in songs:
        combobox.set(last_selected_song)
        offset_var.set(songs.get(last_selected_song, {}).get("offset", 0))
        update_output(f"Reloaded JSON and selected last song: {last_selected_song}")
    else:
        update_output("Reloaded JSON, but last selected song not found in the new data.")
        combobox.set(list(songs.keys())[0])


def combobox_search(event):
    search_term = combobox.get()
    if not search_term:
        combobox['values'] = list(songs.keys())
        return

    lower = search_term.lower()
    starts = [song_id for song_id in songs.keys() if song_id.lower().startswith(lower)]
    contains = [song_id for song_id in songs.keys() if lower in song_id.lower() and not song_id.lower().startswith(lower)]
    matches = starts + contains
    combobox['values'] = matches

    # Preserve the user's typed text and cursor position but do NOT change focus
    try:
        cursor_pos = combobox.index(tk.INSERT)
    except Exception:
        cursor_pos = len(search_term)

    try:
        combobox.icursor(cursor_pos)
    except Exception:
        pass


def combobox_backspace(event):
    """Clear the combobox entry entirely when Backspace is pressed."""
    try:
        combobox.set('')
        combobox['values'] = list(songs.keys())
        try:
            combobox.icursor(0)
        except Exception:
            pass
    except Exception:
        pass
    return "break"


def combobox_open_dropdown(event):
    """Open the combobox dropdown when Enter/Return is pressed in the entry."""
    try:
        combobox.event_generate('<Down>')
    except Exception:
        pass
    return "break"


root = tk.Tk()
root.title("CloneSmith Controller - Guitar Client")

songs = load_songs()

# Top: selection row
top_frame = tk.Frame(root)
top_frame.pack(fill=tk.X, padx=10, pady=8)

label = tk.Label(top_frame, text="Selected Song ID:")
label.grid(row=0, column=0, sticky='w')
combobox = ttk.Combobox(top_frame)
combobox['values'] = list(songs.keys())
combobox.grid(row=0, column=1, sticky='ew', padx=(8,0))

# Button group next to combobox for quick song management
button_frame = tk.Frame(top_frame)
button_frame.grid(row=0, column=2, padx=(8,0))
top_frame.columnconfigure(1, weight=1)

# Time measure enable checkbox
tm_enabled_var = tk.IntVar(value=0)
def _on_tm_toggle():
    enable_time_measure(bool(tm_enabled_var.get()))
tm_check = tk.Checkbutton(button_frame, text='Enable Time Measure', variable=tm_enabled_var, command=_on_tm_toggle)
tm_check.pack(fill=tk.X, pady=2)

last_selected_song = load_last_selected_song()
if last_selected_song in songs:
    combobox.set(last_selected_song)
else:
    combobox.set(list(songs.keys())[0])

offset_var = tk.DoubleVar()
offset_var.set(songs.get(combobox.get(), {}).get("offset", 0))

combobox.bind("<<ComboboxSelected>>", on_combobox_change)
combobox.bind("<KeyRelease>", combobox_search)
combobox.bind('<KeyPress-BackSpace>', combobox_backspace)
combobox.bind('<Return>', combobox_open_dropdown)

# Middle: output area with clear button
output_frame = tk.Frame(root)
output_frame.pack(fill=tk.BOTH, expand=False, padx=10)

output_text = ScrolledText(output_frame, wrap=tk.WORD, width=60, height=12)
output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

output_buttons = tk.Frame(output_frame)
output_buttons.pack(side=tk.LEFT, padx=8, pady=4)
button_clear = tk.Button(output_buttons, text="clear", command=clear_output)
button_clear.pack()

button_reload = tk.Button(output_buttons, text="Reload JSON", command=reload_json)
# Manual reload is obsolete — hide the button when auto-reload is enabled
button_reload.pack_forget()

# Primary actions row
actions_frame = tk.Frame(root)
actions_frame.pack(pady=10)
button_F1 = tk.Button(actions_frame, text="Start Song (F1)", width=18, command=lambda: on_key_press_F1(None))
button_F1.pack(side=tk.LEFT, padx=8)
button_F2 = tk.Button(actions_frame, text="Reset Drums to wait for trigger (F2)", width=28, command=lambda: on_key_press_F2(None))
button_F2.pack(side=tk.LEFT, padx=8)

# Add Song button and dialog
def open_add_song_dialog():
    dlg = tk.Toplevel(root)
    dlg.title("Add Song")
    dlg.grab_set()

    tk.Label(dlg, text="Artist:").grid(row=0, column=0, padx=6, pady=6, sticky='e')
    artist_var = tk.StringVar()
    artist_entry = tk.Entry(dlg, textvariable=artist_var, width=40)
    artist_entry.grid(row=0, column=1, padx=6, pady=6)

    tk.Label(dlg, text="Song Name:").grid(row=1, column=0, padx=6, pady=6, sticky='e')
    song_var = tk.StringVar()
    song_entry = tk.Entry(dlg, textvariable=song_var, width=40)
    song_entry.grid(row=1, column=1, padx=6, pady=6)

    tk.Label(dlg, text="Drum measurement (ms):").grid(row=2, column=0, padx=6, pady=6, sticky='e')
    drum_var = tk.StringVar()
    drum_entry = tk.Entry(dlg, textvariable=drum_var, width=20)
    drum_entry.grid(row=2, column=1, padx=6, pady=6, sticky='w')

    tk.Label(dlg, text="Guitar measurement (ms):").grid(row=3, column=0, padx=6, pady=6, sticky='e')
    guitar_var = tk.StringVar()
    guitar_entry = tk.Entry(dlg, textvariable=guitar_var, width=20)
    guitar_entry.grid(row=3, column=1, padx=6, pady=6, sticky='w')

    # If time-measure has a recent value and the checkbox is enabled, prefill guitar measurement
    try:
        if tm_enabled_var.get() and tm_elapsed_ms:
            guitar_var.set(str(int(tm_elapsed_ms)))
    except Exception:
        pass

    status_lbl = tk.Label(dlg, text="")
    status_lbl.grid(row=4, column=0, columnspan=2, pady=(0,6))

    def validate_inputs(*args):
        a = artist_var.get().strip()
        s = song_var.get().strip()
        d = drum_var.get().strip()
        g = guitar_var.get().strip()
        if not a or not s or not d or not g:
            add_btn.config(state='disabled')
            return
        try:
            int(d)
            int(g)
        except Exception:
            add_btn.config(state='disabled')
            return
        add_btn.config(state='normal')

    artist_var.trace_add('write', validate_inputs)
    song_var.trace_add('write', validate_inputs)
    drum_var.trace_add('write', validate_inputs)
    guitar_var.trace_add('write', validate_inputs)

    def on_add():
        artist = artist_var.get().strip()
        song = song_var.get().strip()
        drum_ms = int(drum_var.get().strip())
        guitar_ms = int(guitar_var.get().strip())

        # Stored offset is the difference between drum and guitar measurements (D - G)
        stored_offset = drum_ms - guitar_ms

        song_id = f"{artist} - {song}"
        record = {"description": song_id, "offset": int(stored_offset)}

        # Load existing songs.json from the working directory and write the new record
        try:
            songs_file = os.path.join(os.path.dirname(__file__), 'songs.json')
            if os.path.exists(songs_file):
                with open(songs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}

            data[song_id] = record

            with open(songs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            update_output(f"Added song: {song_id} (stored offset: {stored_offset} ms)")

            # Refresh UI
            dlg.grab_release()
            dlg.destroy()
            reload_json()
            combobox.set(song_id)
            offset_var.set(stored_offset)
        except Exception as e:
            status_lbl.config(text=f"Error: {e}")

    add_btn = tk.Button(dlg, text="Add", state='disabled', command=on_add)
    add_btn.grid(row=5, column=0, columnspan=2, pady=8)

    # Focus first entry
    artist_entry.focus()


button_add = tk.Button(button_frame, text="Add Song", command=open_add_song_dialog)
button_add.pack(fill=tk.X, pady=2)

# Search on drum server: extract artist from selected combobox entry and send to server
def on_search_button():
    selected = combobox.get().strip()
    if not selected:
        update_output("No song selected to search for.")
        return
    # Extract artist from "Artist - Song" format; fallback to whole string
    if ' - ' in selected:
        artist = selected.split(' - ', 1)[0].strip()
    else:
        artist = selected
    if not artist:
        update_output("Could not determine artist from selection.")
        return
    update_output(f"Searching drums for artist: {artist}")
    send_search_to_drum(artist)

button_search = tk.Button(button_frame, text="Search on Drum Server", command=on_search_button)
button_search.pack(fill=tk.X, pady=2)

def open_edit_song_dialog():
    selected = combobox.get()
    if not selected or selected not in songs:
        update_output("No song selected to edit.")
        return

    dlg = tk.Toplevel(root)
    dlg.title(f"Edit: {selected}")
    dlg.grab_set()

    current_offset = int(songs.get(selected, {}).get('offset', 0))

    tk.Label(dlg, text=f"Editing: {selected}").grid(row=0, column=0, columnspan=3, padx=6, pady=6)
    offset_label = tk.Label(dlg, text=f"Current stored offset: {current_offset} ms")
    offset_label.grid(row=1, column=0, columnspan=3, padx=6, pady=6)

    expl = (
        "Press 'Guitar too early' to increase the stored offset by 250 ms.\n"
        "(This starts drums earlier relative to guitar — use when guitars are too early.)\n\n"
        "Press 'Drums too early' to decrease the stored offset by 250 ms.\n"
        "(This starts drums later relative to guitar — use when drums are too early.)"
    )
    tk.Label(dlg, text=expl, justify='left', wraplength=400).grid(row=2, column=0, columnspan=3, padx=6, pady=6)

    STEP = 250

    def update_offset_display(new_val):
        offset_label.config(text=f"Current stored offset: {new_val} ms")
        # Update combobox and offset_var in main UI
        offset_var.set(new_val)

    def write_offset_to_file(new_val):
        try:
            songs_file = os.path.join(os.path.dirname(__file__), 'songs.json')
            if os.path.exists(songs_file):
                with open(songs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}

            data[selected] = data.get(selected, {})
            data[selected]['description'] = selected
            data[selected]['offset'] = int(new_val)

            with open(songs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            # reload in-memory songs and UI
            reload_json()
            combobox.set(selected)
            update_output(f"Updated offset for '{selected}' to {new_val} ms")
        except Exception as e:
            update_output(f"Error writing songs.json: {e}")

    def on_up():
        nonlocal current_offset
        current_offset = int(current_offset) + STEP
        update_offset_display(current_offset)
        write_offset_to_file(current_offset)

    def on_down():
        nonlocal current_offset
        current_offset = int(current_offset) - STEP
        update_offset_display(current_offset)
        write_offset_to_file(current_offset)

    btn_up = tk.Button(dlg, text=f"Guitar too early (+{STEP} ms)", command=on_up)
    btn_up.grid(row=3, column=0, padx=6, pady=8)
    btn_down = tk.Button(dlg, text=f"Drums too early (-{STEP} ms)", command=on_down)
    btn_down.grid(row=3, column=1, padx=6, pady=8)

    btn_close = tk.Button(dlg, text="Close", command=lambda: (dlg.grab_release(), dlg.destroy()))
    btn_close.grid(row=3, column=2, padx=6, pady=8)


button_edit = tk.Button(button_frame, text="Edit Song", command=open_edit_song_dialog)
button_edit.pack(fill=tk.X, pady=2)

keyboard.on_press_key('F1', on_key_press_F1)
keyboard.on_press_key('F2', on_key_press_F2)

# Also bind keys when the GUI window has focus (fallback / convenience)
try:
    root.bind('<F1>', on_key_press_F1)
    root.bind('<F2>', on_key_press_F2)
except Exception:
    pass

# Start a background watcher to auto-reload songs.json when it changes
songs_path = os.path.join(os.path.dirname(__file__), 'songs.json')
songs_mtime = None

def start_songs_watcher(poll_interval=1.0):
    def watcher():
        global songs_mtime
        while True:
            try:
                new_mtime = os.path.getmtime(songs_path)
            except Exception:
                new_mtime = None

            if songs_mtime is None and new_mtime is not None:
                songs_mtime = new_mtime
            elif new_mtime is not None and songs_mtime is not None and new_mtime != songs_mtime:
                songs_mtime = new_mtime
                try:
                    root.after(0, reload_json)
                except Exception:
                    pass

            time.sleep(poll_interval)

    t = threading.Thread(target=watcher, daemon=True)
    t.start()

start_songs_watcher()

root.mainloop()