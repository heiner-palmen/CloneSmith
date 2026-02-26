import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import json
import keyboard
import time
import socket

def send_drum_trigger():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #kqhadc4uitbodrep.myfritz.net
    #192.168.0.50
    client.connect(('kqhadc4uitbodrep.myfritz.net', 12345))  # Connect to the server IP and port

    trigger = "StartAction"  # Replace with your trigger
    client.send(trigger.encode('utf-8'))

    client.close()

def on_combobox_change(event):
    selected_song_id = combobox.get()
    selected_song = songs.get(selected_song_id, {"offset": 0})
    offset_var.set(selected_song["offset"])
    update_output(f"Selected Song ID: {selected_song_id}, Offset: {offset_var.get()}")

def update_output(message):
    output_text.insert(tk.END, f"{message}\n")
    output_text.see(tk.END)  # Scroll to the bottom
    
def clear_output():
    output_text.delete(1.0, tk.END)

def on_key_press_q(event):
    milliseconds = offset_var.get()
    play_songs(milliseconds) 
    update_output(f"Pressing Enter")
    keyboard.press_and_release('enter')

def play_guitar():
    keyboard.press_and_release('enter')

def play_drums():
    send_drum_trigger()    

def play_songs(milliseconds):
    if milliseconds < 0:
        update_output(f"Trigger start guitar")
        play_guitar()
        # Start guitar song after waiting for the absolute value of milliseconds
        update_output(f"Waiting... Offset: {milliseconds}")
        time.sleep(abs(milliseconds) / 1000)
        update_output(f"Trigger start drums")
        # Start drums song
        play_drums()
    else:
        # Start drums song
        update_output(f"Trigger start drums")
        play_drums()
        # Wait for milliseconds before starting guitar song
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

root = tk.Tk()
root.title("Song Selector")

songs = load_songs()

label = tk.Label(root, text="Selected Song ID:")
label.pack(pady=10)

combobox = ttk.Combobox(root, values=list(songs.keys()))
combobox.pack()

if songs:
    combobox.set(list(songs.keys())[0])

offset_var = tk.DoubleVar()
offset_var.set(songs.get(combobox.get(), {}).get("offset", 0))

combobox.bind("<<ComboboxSelected>>", on_combobox_change)

output_text = ScrolledText(root, wrap=tk.WORD, width=40, height=10)
output_text.pack(pady=10)

button = tk.Button(root, text="clear", command=clear_output)
button.pack(pady=10)

# Bind the 'q' key press event globally
keyboard.on_press_key('q', on_key_press_q)

root.mainloop()