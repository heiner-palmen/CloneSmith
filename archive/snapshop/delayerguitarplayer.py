import keyboard
import time

def main():
    milliseconds = read_elapsed_time_from_file()

    print(f"Press 'q' to wait for {milliseconds:.2f} milliseconds and then press Enter.")
    keyboard.wait('q')
    
    print("Waiting...")
    time.sleep(milliseconds / 1000)  # Convert milliseconds to seconds
    keyboard.press_and_release('enter')
    
    print("Done!")

def read_elapsed_time_from_file():
    try:
        with open("localsongoffset.txt", "r") as file:
            elapsed_time = float(file.read())
            return elapsed_time
    except FileNotFoundError:
        print("Error: localsongoffset.txt not found.")
        return 0
    except ValueError:
        print("Error: Invalid content in localsongoffset.txt.")
        return 0

if __name__ == "__main__":
    main()