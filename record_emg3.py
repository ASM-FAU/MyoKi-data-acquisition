import yaml  
import pandas as pd  
import threading  
import time  
from datetime import datetime  
from pytrignos import Sensor  
import os  

emg_error_event = threading.Event()


class EMGRecorder:
    """
    Class to handle EMG and auxiliary sensor data recording from Trigno sensors.
    """
    
    def __init__(self, config_path="config.yaml"):
        # Initialize with path to config file, load settings, and set up the sensor
        self.config_path = config_path
        self.load_config()  # Load settings from YAML
        self.sensor = self.initialize_sensor()  # Set up sensor based on config
        self.old_time=0
        self.emg_data = []  # List to store EMG data frames
        self.aux_data = []  # List to store auxiliary data frames
        self.participant_num = 1  # Default participant ID
        self.action_label = 1  # Default action label
        self.stop_event = threading.Event()  # Event to signal thread stop
        self.lock = threading.Lock()  # Lock for thread-safe access to shared data
        # Sensor value tracking
        self.emg_last_values = {}  # Track last values of each EMG sensor
        self.emg_last_updated = {}  # Track last update time for each EMG sensor
        self.aux_last_values = {}  # Track last values of each auxiliary sensor
        self.aux_last_updated = {}  # Track last update time for each auxiliary sensor
        self.stale_duration = 5  # Time in seconds for which a value must remain the same to trigger a warning
        self.emg_last_log_time = {}  # Track last log time for EMG sensors
        self.aux_last_log_time = {}  # Track last log time for auxiliary sensors

    def load_config(self):
        """
        Loads sensor and recording settings from a YAML config file.
        """
        with open(self.config_path, "r") as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)  # Load YAML config
        self.EMGSensorID = self.config['sensors_labels']  # List of EMG sensor labels
        self.AuxSensorID = self.determine_aux_sensor_ids()  # Generate aux sensor IDs based on config
        # Set data paths from config
        self.input_data_path = self.config['input_data_path']
        self.output_data_path = self.config['output_data_path']
        self.processing_data_path = self.config['processing_data_path']
    def determine_aux_sensor_ids(self):
        """
        Generates auxiliary sensor IDs based on config options for orientation, accelerometer, and gyroscope data.
        """
        aux_sensor_ids = []
        if self.config['read_orientation']:
            # Add orientation sensor IDs if enabled
            for label in self.config['sensors_labels']:
                aux_sensor_ids += [f"{label}_re", f"{label}_im_x", f"{label}_im_y", f"{label}_im_z"]
        else:
            # Add accelerometer and/or gyroscope sensor IDs if enabled
            for label in self.config['sensors_labels']:
                if self.config['read_acc']:
                    aux_sensor_ids += [f"{label}_acc_x (g)", f"{label}_acc_y (g)", f"{label}_acc_z (g)"]
                if self.config['read_gyro']:
                    aux_sensor_ids += [f"{label}_gyr_x (deg/s)", f"{label}_gyr_y (deg/s)", f"{label}_gyr_z (deg/s)"]
        return aux_sensor_ids

    def initialize_sensor(self):
        """
        Initializes the Sensor instance with parameters from the configuration.
        """
        return Sensor(
            self.config['aquisition_mode'], self.config['sensors_mode_number'], self.config['read_emg'],
            self.config['read_acc'], self.config['read_gyro'], self.config['read_orientation'],
            self.config['sensor_ids'], self.config['sensors_labels'], self.config['host'],
            self.config['cmd_port'], self.config['emg_port'], self.config['aux_port'], self.config['timeout']
        )

    def start_recording(self):
        """
        Begins recording by clearing any existing data, resetting stop flag, and launching data collection thread.
        """
        self.emg_data = []  # Clear existing EMG data
        self.aux_data = []  # Clear existing auxiliary data
        self.stop_event.clear()  # Reset stop flag
        threading.Thread(target=self.record_data).start()  # Start data recording thread


    def record_data(self):

        global main_loop_flag
        """
        Collects EMG and auxiliary sensor data continuously until the stop event is set.
        """
        self.sensor.start_acquisition() 
        last_data_time = time.time()  # Initialize the last data timestamp

        while not self.stop_event.is_set():

            current_time = time.time()  # Get the current time

            with self.lock:  # Ensure action label consistency across threads
                emg_data, aux_data = self.sensor.get_sensor_data()  # Read sensor data
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Timestamp with millisecond precision
                action_label = self.action_label

            # Check if EMG data is valid
            if emg_data.size > 0:
                emg_df = pd.DataFrame(data=emg_data.transpose())  # Create DataFrame for EMG 
                emg_df.insert(0, 'Timestamp', timestamp)  # Add Timestamp column
                emg_df['Action_Label'] = action_label  # Add action label column
                with self.lock:  
                    self.emg_data.append(emg_df)
                last_data_time = current_time  # Update last data time
                emg_error_event.clear()

            # Check if auxiliary data is valid
            if aux_data.size > 0:
                aux_df = pd.DataFrame(data=aux_data.transpose())  # Create DataFrame for auxiliary data
                aux_df.insert(0, 'Timestamp', timestamp)  # Add Timestamp column
                with self.lock:  
                    self.aux_data.append(aux_df)
                last_data_time = current_time  # Update last data time
                

            # Check if no data has been received in the last 5 seconds
            if current_time - last_data_time >= 1:

                emg_error_event.set()
                print(f"No data received for 1 seconds. Current action label: {action_label}")


        self.sensor.stop_acquisition()  # Stop data acquisition when recording is complete


            
    def update_participant_action(self, pn, al):
        """
        Updates participant number and action label for the current recording.
        """
        self.participant_num = pn  # Update participant ID
        with self.lock:
            self.action_label = al  # Update action label with thread safety


    def stop_recording(self, participant_num,test_number):
        """
        Stops data recording and saves the collected data to CSV files.
        """ 
        self.stop_event.set()  # Signal to stop recording
        with self.lock:

            if self.emg_data or self.aux_data:  # Save data if any is recorded
                self.save_data(participant_num,test_number)
            self.emg_data = []  # Clear EMG data list
            self.aux_data = []  # Clear auxiliary data list

    def save_data(self, participant_num, test_number):
        """
        Saves collected EMG and auxiliary data to CSV files.
        Appends data to the existing files if they already exist.
        """
        if not self.emg_data or not self.aux_data:
            print("No data recorded. Skipping save.")
            return
        
        # Concatenate all recorded data into DataFrames
        emg_df = pd.concat(self.emg_data, ignore_index=True) if self.emg_data else pd.DataFrame()
        aux_df = pd.concat(self.aux_data, ignore_index=True) if self.aux_data else pd.DataFrame()

        # Define file paths based on participant and test number
        base_path = f'{self.input_data_path}/{test_number}'  # Path for input data
        output_path = f'{self.processing_data_path}/{test_number}'  # Path for processed data
        final_data = f'{self.output_data_path}/{test_number}'  # Path for final data
        
        # Create directories if they don't exist
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(final_data, exist_ok=True)

        # Save EMG data to CSV (append mode)
        if not emg_df.empty:
            emg_file = f'{base_path}/emg_data_P{participant_num}.csv'
            
            # Check if the file already exists to determine whether to append or create a new file
            if os.path.exists(emg_file):
                # Append the data to the existing file (without writing headers)
                emg_df.to_csv(emg_file, mode='a', header=False, index=False)
                print(f"EMG data appended to {emg_file}.")
            else:
                # Create a new file and write the data with headers
                emg_df.to_csv(emg_file, index=False)
                print(f"EMG data saved to {emg_file}.")
        else:
            print("No EMG data recorded.")

        # Save auxiliary data to CSV (append mode)
        if not aux_df.empty:
            aux_file = f'{base_path}/aux_data_P{participant_num}.csv'
            
            # Check if the file already exists to determine whether to append or create a new file
            if os.path.exists(aux_file):
                # Append the data to the existing file (without writing headers)
                aux_df.to_csv(aux_file, mode='a', header=False, index=False)
                print(f"Auxiliary data appended to {aux_file}.")
            else:
                # Create a new file and write the data with headers
                aux_df.to_csv(aux_file, index=False)
                print(f"Auxiliary data saved to {aux_file}.")
        else:
            print("No auxiliary data recorded.")
