import csv  
import time  
from datetime import datetime 
from cyberglove import CyberGlove  
import threading  
import os  



glove_error_event = threading.Event()


is_recording = False  # Flag indicating if recording is active
raw_data_list = []  # List to store recorded data temporarily

# Configuration for sensor value monitoring
x_seconds = 20  # Duration to monitor unchanged sensor values
print_interval = 2  # Interval to print warnings (in seconds)
sensor_value_tracking = {}  # Dictionary to track sensor values and their unchanged durations
last_print_time = {}  # Dictionary to track last print time for each sensor

def initialize_cyberglove():
    """Initializes the CyberGlove device and starts communication."""
    cg = CyberGlove(n_df=18, s_port='COM9', samples_per_read=1)  # Initialize CyberGlove with 18 sensors on COM8
    cg.start()  # Start CyberGlove data acquisition
    return cg  # Return initialized glove instance

def monitor_sensor_values(raw_data):
    """Monitors sensor values and triggers an event if unchanged for too long."""
    global sensor_value_tracking, last_print_time
    
    current_time = time.time()  # Get current time at the start to avoid calling multiple times in loop

    # Loop through each sensor data
    for sensor_index, value in enumerate(raw_data):
        if sensor_index not in sensor_value_tracking:
            # Initialize tracking for this sensor
            sensor_value_tracking[sensor_index] = {'value': value, 'duration': 0}
            last_print_time[sensor_index] = current_time  # Initialize print time for this sensor

        # Check if the current value matches the last recorded value
        if sensor_value_tracking[sensor_index]['value'] == value:
            # Increment the duration if the value hasn't changed
            sensor_value_tracking[sensor_index]['duration'] += 1 / 150  # Time increment based on sample rate
            
            # Trigger event if the value is unchanged for 20 seconds
            if sensor_value_tracking[sensor_index]['duration'] >= 20:
                glove_error_event.set()  # Trigger the event if the value is unchanged for 20 seconds
                
                # Log the warning (optional)
                #print(f"Warning: Sensor {sensor_index} value unchanged for 20 seconds.")

                # Reset duration tracking to avoid repeated triggering
                sensor_value_tracking[sensor_index]['duration'] = 0
        else:
            # Reset the tracking for the changed sensor
            sensor_value_tracking[sensor_index] = {'value': value, 'duration': 0}
            last_print_time[sensor_index] = current_time  # Reset print time for this sensor


def record_cyberglove(cg):
    """Reads data from CyberGlove at regular intervals and stores it in raw_data_list."""
    global is_recording, raw_data_list
    is_recording = True  # Set recording flag to True
    raw_data_list = []  # Clear any old data
    interval = 1 / 150  # Sampling interval for CyberGlove (150 Hz)

    try:
        while is_recording:
            start_cycle = time.time()  # Record start time of the cycle
            raw_data = cg.read()  # Read sensor data from CyberGlove
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Timestamp with millisecond precision
            data_row = [timestamp] + raw_data.reshape(-1,).tolist()  # Append timestamp to data row
            raw_data_list.append(data_row)  # Store data row in list
            
            # Monitor the sensor values for changes
            monitor_sensor_values(raw_data)

            # Calculate remaining time in cycle and wait to maintain consistent sampling rate
            end_cycle = time.time()
            time_to_wait = interval - (end_cycle - start_cycle)
            if time_to_wait > 0:
                time.sleep(time_to_wait)  # Wait for the remaining time in interval
    except KeyboardInterrupt:
        print("Recording manually stopped.")  # Handle manual interruption gracefully

def start_recording_thread(cg):
    """Starts a separate thread for CyberGlove data recording.""" 
    thread = threading.Thread(target=record_cyberglove, args=(cg,))
    thread.daemon = True  # Set thread as daemon so it closes with main program
    thread.start()  # Start the recording thread
    return thread  # Return the thread handle

def stop_cyberglove(cg, filename):
    """Stops data recording and writes collected data to a CSV file.""" 
    global is_recording
    is_recording = False  # Stop recording flag
    time.sleep(0.2)  # Allow time for any last read operations

    # Check if the CSV file already exists
    file_exists = os.path.isfile(filename)
    
    # Open file in append mode to avoid overwriting data
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        
        # Write header row if creating a new file
        if not file_exists:
            writer.writerow(['Timestamp'] + ['Sensor' + str(i) for i in range(18)])  # Header with sensor names
        
        # Write all recorded data rows to the file
        writer.writerows(raw_data_list)
    
    cg.stop()  # Stop CyberGlove data acquisition

# Main script to demonstrate initialization, recording, and stopping
if __name__ == '__main__':
    cg = initialize_cyberglove()  # Initialize CyberGlove
    thread = start_recording_thread(cg)  # Start recording in a separate thread

    # Main thread can perform other tasks while data is being recorded
    try:
        time.sleep(5)  # Recording for 5 seconds
        stop_cyberglove(cg, 'cyberglove_readings.csv')  # Stop recording and save data

        # Reinitialize CyberGlove and record again for another 5 seconds
        cg = initialize_cyberglove()  
        thread = start_recording_thread(cg)
        time.sleep(5)
        
        stop_cyberglove(cg, 'cyberglove_readings.csv')  # Stop and save second recording
    except KeyboardInterrupt:
        # Gracefully stop recording if interrupted manually
        stop_cyberglove(cg, 'cyberglove_readings.csv')
