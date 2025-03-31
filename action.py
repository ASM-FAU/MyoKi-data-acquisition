import threading
import time
import record_emg3 as emg
import record_fmg as fmg
import record_cyberglove as glove
import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel, Label
from PIL import Image, ImageTk



# Initialize global variableskhhn
emg_recorder = None
gesture_thread = None
stop_gesture_event = threading.Event()  
fmg_initialized = False
main_loop_flag = True
participant_num = 1
action_num = 0
test_number = 1
set_action_button = None
init_condition = threading.Condition()
popup = None  # Reference to the image popup
timer_label = None  # Reference to the timer label
timer_thread = None
stop_timer_event = threading.Event()
glove_recorder=None

# starts the Mqtt connection
def initialize_sys():
    global fmg_initialized

    with init_condition:
        if not fmg_initialized:
            threading.Thread(target=fmg.read_serial, daemon=True).start()
            init_condition.wait(timeout=2)
            fmg_initialized = True
            print("FMG initialization started. Waiting for the first message to confirm initialization.")

# Starts the Measurement and runs it, while main_loop_flag is true
def action_task(participant_num):
    try:

        global emg_recorder,glove_recorder
        emg_recorder = emg.EMGRecorder()
        threading.Thread(target=fmg.start_recording, args=(participant_num, test_number)).start()
        print(f"FMG recording started for participant {participant_num}.")

        glove_recorder = glove.initialize_cyberglove()
        glove.start_recording_thread(glove_recorder)
        print("Cyberglove recording started.")

        emg_recorder.start_recording()
        emg_recorder.update_participant_action(participant_num, action_num)
        print("EMG recording started.")

        

        while main_loop_flag:
            emg_recorder.update_participant_action(participant_num, action_num)
            time.sleep(1)

    except Exception as e:
        error_message = f"Error in gesture classification task: {str(e)}"
        print(error_message)


# stops the gui and save everything
def quit_program():
    global main_loop_flag, emg_recorder, glove_recorder, gesture_thread

    # Safely stop all recording and devices
    main_loop_flag = False

    try:
        fmg.stop_recording()
        print("FMG recording stopped.")
        time.sleep(1)
        if emg_recorder:
            emg_recorder.stop_recording(participant_num, test_number)
            print("EMG recording stopped.")


        if glove_recorder:
            glovefile = f'../data/input_data/{test_number}/glove_data_P{participant_num}.csv'
            glove.stop_cyberglove(glove_recorder, glovefile)
            print("Cyberglove recording stopped.")
        

    except Exception as e:
        print(f"Error during shutdown: {str(e)}")

    # Join the gesture thread to ensure it completes before exiting
    if gesture_thread:
        gesture_thread.join()
        print("Gesture thread has completed.")

    
    # Terminate the GUI loop
    root.quit()

# automatic increases the number of the action lable
def increment_action_number():
    """Increment the value 1in the action entry field by 1 and display the updated action's image."""
    global popup
    try:
        # Increment the action number
        current_value = int(action_entry.get())
        action_entry.delete(0, tk.END)
        action_entry.insert(0, str(current_value + 1))
        
        # Close the existing popup (if any) to avoid multiple windows
        if popup:
            popup.destroy()
            popup = None

        # Display the new image
        show_image(0)
    except ValueError:
        action_entry.delete(0, tk.END)
        action_entry.insert(0, "1")  # Default to 1 if the field is empty or invgalid


# displays the image of the recent action 
def show_image(first_image):
    """Display the image for the selected action number."""
    global popup
    try:
        if first_image: 
            current_action_num=1  
        else:
            current_action_num = int(action_entry.get())

        if current_action_num <= 0:
            current_action_num=1

        image_path = f'../images/Final_Images/action_{current_action_num}.jpg'
        img = Image.open(image_path)
        img = img.resize((1500, 920), Image.Resampling.LANCZOS)

        popup = Toplevel(root)
        popup.title(f"Action {current_action_num} Image")
        x_offset = 1200  # Die Breite des linken Monitors
        y_offset = 0   # Vertikale Position des Fensters
        popup.geometry(f"1500x920+{x_offset}+{y_offset}")

        tk_img = ImageTk.PhotoImage(img)
        img_label = Label(popup, image=tk_img)
        img_label.image = tk_img
        img_label.pack(pady=10)
        close_btn = tk.Button(popup, text="Close", font=("Helvetica", 12, "bold"), bg="#555555", fg="white",
                              command=popup.destroy)
        close_btn.pack(pady=10)
    except FileNotFoundError:
        messagebox.showerror("Image Not Found", f"Image for action {current_action_num} not found.")
    except Exception as e:
        messagebox.showerror("Error", f"Error displaying image: {str(e)}")

# starts the timer
def start_timer():
    """Start the timer and display the timer label."""
    global timer_label, stop_timer_event
    stop_timer_event.clear()

    def update_timer():
        seconds = 0
        while not stop_timer_event.is_set():
            try:
                minutes, sec = divmod(seconds, 60)
                timer_label.config(text=f"Timer: {minutes:02}:{sec:02}")
                seconds += 1
                time.sleep(1)
            except Exception as e:
             print(f"TclError caught: {e}")

    if not timer_label:
        timer_label = tk.Label(main_frame, text="Timer: 00:00", font=("Helvetica", 12), bg="#f0f0f0")
        timer_label.pack(pady=5)
    timer_thread = threading.Thread(target=update_timer, daemon=True)
    timer_thread.start()

# stops the timer
def stop_timer():
    """Stop the timer and remove the timer label."""
    global timer_label
    stop_timer_event.set()
    if timer_label:
        timer_label.destroy()
        timer_label = None

# updates the lable 
def update_leds():
    """Update LED colors based on error flags."""
    emg_led.config(bg="green" if not emg.emg_error_event.is_set() else "red")
    fmg_led.config(bg="green" if not fmg.fmg_error_event.is_set() else "red")
    glove_led.config(bg="green" if not glove.glove_error_event.is_set() else "red")
    root.after(1000, update_leds)  # Repeat every second

# Sets the Action label in the data 
def set_action_number():
    global action_num
    try:
        action_number = int(action_entry.get())
        action_num = action_number
        emg_recorder.update_participant_action(participant_num, action_num)
        status_label.config(text=f"Action number updated to {action_num}.")
        set_action_button.config(state=tk.DISABLED)
        start_timer()  # Start the timer when action is set
    except ValueError:
        status_label.config(text="Invalid action number. Please enter a valid integer.")


def set_action_to_zero():
    """Stop the timer, close the image popup, reset the action label to 0, and increment the action number in the text field."""
    global popup, action_num
    stop_timer()  # Stop the timer
    
    # Close the image popup if it's open
    if popup:
        popup.destroy()
        popup = None

    # Increment the action number in the text field
    try:
        current_value = int(action_entry.get())
        new_value = current_value + 1
        action_entry.delete(0, tk.END)  # Clear the text field
        action_entry.insert(0, str(new_value))  # Insert the incremented value
    except ValueError:
        action_entry.delete(0, tk.END)
        action_entry.insert(0, "1")  # Default to 1 if invalid or empty
    show_image(0)
    # Reset the action number and update the label
    action_num = 0
    emg_recorder.update_participant_action(participant_num, action_num)
    status_label.config(text="Action number set to 0.")
    set_action_button.config(state=tk.NORMAL)


# Main Application
if __name__ == "__main__":
    test_number = simpledialog.askinteger("Input", "Enter Test Number:", minvalue=1)
    participant_num = simpledialog.askinteger("Input", "Enter Participant Number:", minvalue=1)

    test_number=f'P{participant_num}/{test_number}'

    initialize_sys()  # Initialize FMG and wait for it to be ready

        
    # Initialize Tkinter UI
    root = tk.Tk()
    root.title("EMG Action Control")

    # Set window size and position
    window_width = 400
    window_height = 600
    
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2) + 300
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Create a main frame
    main_frame = tk.Frame(root, padx=10, pady=10, bg="#f0f0f0")
    main_frame.pack(expand=True)

    # Add widgets to the main frame
    tk.Label(main_frame, text="EMG Action Control", font=("Helvetica", 16, "bold"), bg="#f0f0f0").pack(pady=10)
    tk.Label(main_frame, text="Enter Action Number:", font=("Helvetica", 12), bg="#f0f0f0").pack(pady=5)

    # Create a frame for the text field and the "+" button to be placed side by side
    input_frame = tk.Frame(main_frame, bg="#f0f0f0")
    input_frame.pack(pady=5)

    # "+" Button (on the left of the entry field)
    increment_button = tk.Button(input_frame, text="+", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", command=increment_action_number)
    increment_button.pack(side="left", padx=5)

    # Action number entry field (next to the "+" button)
    action_entry = tk.Entry(input_frame, font=("Helvetica", 12), justify="center")
    action_entry.pack(side="left", padx=5)

    # Create a button frame for other buttons (Show, Start, Stop, Quit)
    button_frame = tk.Frame(main_frame, bg="#f0f0f0")
    button_frame.pack(pady=5)

    # Buttons
    show_button = tk.Button(button_frame, text="Show", font=("Helvetica", 12, "bold"), bg="#007BFF", fg="white", command=show_image(1))
    show_button.pack(side="left", padx=5)

    set_action_button = tk.Button(button_frame, text="Start", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", command=set_action_number)
    set_action_button.pack(side="left", padx=5)

    end_button = tk.Button(button_frame, text="Stop", font=("Helvetica", 12, "bold"), bg="#F44336", fg="white", command=set_action_to_zero)
    end_button.pack(side="left", padx=5)

    quit_button = tk.Button(button_frame, text="Quit", font=("Helvetica", 12, "bold"), bg="#555555", fg="white", command=quit_program)
    quit_button.pack(side="left", padx=5)

    # Status/Error Label (this will be placed below the text entry field)
    status_label = tk.Label(main_frame, text="", font=("Helvetica", 12), bg="#f0f0f0", fg="red")
    status_label.pack(pady=10)

    # LED indicators
    led_frame = tk.Frame(main_frame, bg="#f0f0f0")
    led_frame.pack(pady=10)
    emg_led = tk.Label(led_frame, text="EMG", font=("Helvetica", 10), bg="gray", width=10)
    emg_led.pack(side="left", padx=5)
    fmg_led = tk.Label(led_frame, text="FMG", font=("Helvetica", 10), bg="gray", width=10)
    fmg_led.pack(side="left", padx=5)
    glove_led = tk.Label(led_frame, text="Glove", font=("Helvetica", 10), bg="gray", width=10)
    glove_led.pack(side="left", padx=5)

    update_leds()  # Start the LED update loop

    # Start the gesture recording task
    gesture_thread = threading.Thread(target=action_task, args=(participant_num,))
    gesture_thread.start()

    # Run the main loop
    root.protocol("WM_DELETE_WINDOW", quit_program)
    root.mainloop()
