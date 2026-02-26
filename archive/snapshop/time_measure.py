#py -m pip install --upgrade pip
#py -m pip install keyboard
#pip install keyboard
import keyboard
import time
import sys

def on_key_event(event):
    global start_time
    global elapsed_time
    global press_count

    if event.event_type == keyboard.KEY_DOWN and (event.name == 'a' or event.name == 'enter'):
        press_count += 1
        if start_time is None:
            print("Stopwatch started.")
            start_time = time.time()
        else:
            elapsed_time = (time.time() - start_time) * 1000
            print(f"Stopwatch stopped. Elapsed time: {elapsed_time:.2f} milliseconds.")
            save_elapsed_time(elapsed_time)
            start_time = None

        if press_count == 2:
            print("Exiting...")
            keyboard.unhook_all()
            time.sleep(1)
            sys.exit()

def save_elapsed_time(elapsed_time):
    with open("localsongoffset.txt", "w") as file:
        file.write(str(elapsed_time))

def main():
    global start_time
    global elapsed_time
    global press_count

    start_time = None
    elapsed_time = 0
    press_count = 0

    print("Press 'a' or 'Enter/Return' to start/stop the stopwatch.")

    keyboard.hook(on_key_event)
    keyboard.wait()  # Wait for events

if __name__ == "__main__":
    main()