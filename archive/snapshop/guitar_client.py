import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import json
import keyboard
import time
import socket

heiner_host = 'ootb.webredirect.org'

def send_drum_start_trigger():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((heiner_host, 12345))  # Connect to the server IP and port

    trigger = "StartAction"
    client.send(trigger.encode('utf-8'))

    client.close()


def send_drum_pause_trigger():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((heiner_host, 12345))  # Connect to the server IP and port

    trigger = "PauseAction"
    client.send(trigger.encode('utf-8'))

    client.close()


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


def on_key_press_q(event):
    milliseconds = offset_var.get()
    play_songs(milliseconds)


def on_key_press_w(event):
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
        with open("songs.json", "r") as file:
            songs_data = json.load(file)
        return songs_data
    except FileNotFoundError:
        print("Error: songs.json not found.")
        return {}


def save_last_selected_song(song_id):
    with open("last_selected_song.txt", "w") as file:
        file.write(song_id)


def load_last_selected_song():
    try:
        with open("last_selected_song.txt", "r") as file:
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
    values = [song_id for song_id in songs.keys() if search_term.lower() in song_id.lower()]
    combobox['values'] = values


root = tk.Tk()
root.title("Song Selector")

songs = load_songs()

label = tk.Label(root, text="Selected Song ID:")
label.pack(pady=10)

combobox = ttk.Combobox(root)
combobox['values'] = list(songs.keys())
combobox.pack()

last_selected_song = load_last_selected_song()
if last_selected_song in songs:
    combobox.set(last_selected_song)
else:
    combobox.set(list(songs.keys())[0])

offset_var = tk.DoubleVar()
offset_var.set(songs.get(combobox.get(), {}).get("offset", 0))

combobox.bind("<<ComboboxSelected>>", on_combobox_change)
combobox.bind("<KeyRelease>", combobox_search)

output_text = ScrolledText(root, wrap=tk.WORD, width=40, height=10)
output_text.pack(pady=10)

button = tk.Button(root, text="clear", command=clear_output)
button.pack(pady=10)

button_reload = tk.Button(root, text="Reload JSON", command=reload_json)
button_reload.pack(pady=10)

button_q = tk.Button(root, text="Start Song", command=lambda: on_key_press_q(None))
button_q.pack(pady=10)

button_w = tk.Button(root, text="Reset Drums to wait for trigger", command=lambda: on_key_press_w(None))
button_w.pack(pady=10)

keyboard.on_press_key('F1', on_key_press_q)
keyboard.on_press_key('F2', on_key_press_w)
root.mainloop()