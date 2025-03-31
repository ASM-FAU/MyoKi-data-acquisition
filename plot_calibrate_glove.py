import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import numpy as np
from record_cyberglove import CyberGlove  # Import your CyberGlove module

# Initialize CyberGlove
glove = CyberGlove(n_df=18, s_port='COM9', samples_per_read=1)
glove.start()

# GUI Setup
root = tk.Tk()
root.title("CyberGlove Live Sensor Viewer")
root.geometry("500x400")

# Global variables
selected_sensor = 0
sensor_value = tk.StringVar(value="Waiting...")
data = []

# Function to update sensor value in real-time
def update_sensor():
    global data
    while True:
        raw_data = glove.read()
        value = float(raw_data[selected_sensor])  # Convert to float
        sensor_value.set(f"Sensor {selected_sensor}: {value:.3f}")
        data.append(value)
        if len(data) > 50:
            data.pop(0)
        time.sleep(0.1)  # Update every 100ms

# Function to update plot
def update_plot():
    while True:
        ax.clear()
        ax.plot(data, marker='o', linestyle='-')
        ax.set_title(f"Live Sensor {selected_sensor} Data")
        ax.set_ylim(0,300)  # Adjust according to expected range
        canvas.draw()
        time.sleep(0.5)

tk.Label(root, text="Select Sensor:").pack()
sensor_dropdown = ttk.Combobox(root, values=[i for i in range(18)], state='readonly')
sensor_dropdown.pack()
sensor_dropdown.current(0)

def on_sensor_change(event):
    global selected_sensor
    selected_sensor = int(sensor_dropdown.get())

if __name__ == "__main__":
    sensor_dropdown.bind("<<ComboboxSelected>>", on_sensor_change)

    tk.Label(root, textvariable=sensor_value, font=("Arial", 16)).pack()

    # Plot setup
    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()

    # Start threads
    threading.Thread(target=update_sensor, daemon=True).start()
    threading.Thread(target=update_plot, daemon=True).start()

    root.mainloop()
