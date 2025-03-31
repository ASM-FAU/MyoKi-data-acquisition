import matplotlib.pyplot as plt
import queue
import threading
import struct
import time
import serial

# Serielle Verbindung konfigurieren
serial_port = 'COM13'  # Passe dies an deinen Port an (z. B. 'COM3' unter Windows)
baud_rate = 115200  # Baudrate, passend zum Arduino
default_value = 3.292814016342163
message_queue = queue.Queue(maxsize=10000)
is_recording = False
stop_fmg = 0
sensor_0_data = []  # List to store sensor 0 data
timestamps = []  # Store timestamps for each data point
max_data_length = 100  # Store only the last 100 values

# Set up the plotting figure and axis
plt.ion()  # Turn on interactive mode for live updating
fig, ax = plt.subplots()
line, = ax.plot([], [], label="Sensor 0 Data")
ax.set_xlabel("Time (Index)")
ax.set_ylabel("Sensor Value")
ax.set_title("Live Sensor Data")
ax.legend()

# Thread event for synchronization
plot_event = threading.Event()

def read_serial():
    global is_recording, stop_fmg
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Verbindung zu {serial_port} hergestellt.")

        while not stop_fmg:
            if ser.in_waiting > 0:
                start_delim = ser.read(1)
                if start_delim == b'\xFF':  
                    timestamp_bytes = ser.read(8)  # Read timestamp
                    timestamp = struct.unpack('Q', timestamp_bytes)[0]

                    sensor_data = []
                    for i in range(24):
                        sensor_bytes = ser.read(4)
                        sensor_value = struct.unpack('f', sensor_bytes)[0]
                        sensor_data.append(sensor_value)

                    end_delim = ser.read(1)
                    if end_delim == b'\x00':
                        # Store data for sensor 0 (or any other sensor)
                        sensor_0_data.append(sensor_data[0])  # Example for sensor 0
                        timestamps.append(timestamp)  # Store the timestamp

                        # Keep only the last 'max_data_length' values
                        if len(sensor_0_data) > max_data_length:
                            sensor_0_data.pop(0)  # Remove the oldest value
                            timestamps.pop(0)  # Remove the oldest timestamp

                        # Check if the timestamp fits the current PC time
                        if timestamp <= int(time.time()) and not is_recording:
                            is_recording = True  # Start recording/plotting once the timestamp fits
                            print(f"Started plotting at timestamp {timestamp}")

                        # Set the event to update the plot
                        if is_recording:
                            plot_event.set()

    except serial.SerialException as e:
        print(f"Fehler bei der seriellen Verbindung: {e}")
        stop_fmg = 1  # Stop the data collection on error

def update_plot():
    """Update the plot with the latest sensor data."""
    # Update the data of the plot
    line.set_xdata(range(len(sensor_0_data)))  # x-axis: Index of the data points
    line.set_ydata(sensor_0_data)  # y-axis: Sensor 0 values

    # Recalculate limits based on the new data
    ax.relim()  # Recalculate limits
    ax.autoscale_view()  # Rescale the axes based on the new data

    # Set y-axis limits explicitly between 0 and 3.3
    ax.set_ylim(0, 4)

    # Redraw the updated plot
    plt.draw()
    plt.pause(0.1)  # Pause for a short time to update the plot (0.1 seconds)

if __name__ == "__main__":
    # Start the serial read thread
    serial_thread = threading.Thread(target=read_serial)
    serial_thread.start()

    # Display the plot in the main thread
    while True:
        if plot_event.is_set():  # Check if new data is available
            update_plot()
            plot_event.clear()  # Reset the event
        plt.pause(0.1)  # Small pause to update the plot
