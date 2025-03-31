import pandas as pd
import os
import numpy as np
from scipy.io import savemat,loadmat
from datetime import datetime

def data_integration_processing_interpolate(
        global_emg_file_path, 
        global_aux_file_path, 
        global_fmg_file_path, 
        glove_file_path, 
        output_file_path,
        sensor_list,
        repetition_value,
        excluded_sensor='S8'
        ):
    
    # Load CSV files with parsed timestamps

    emg_df = pd.read_csv(global_emg_file_path, dtype={'Timestamp': 'object'})

    # Convert 'Timestamp' column to datetime with microsecond precision
    emg_df['Timestamp'] = pd.to_datetime(emg_df['Timestamp'], format='%Y-%m-%d %H:%M:%S.%f')
   
    # Load other datasets
    aux_df = pd.read_csv(global_aux_file_path, dtype={'Timestamp': 'object'})
    aux_df ['Timestamp'] = pd.to_datetime(aux_df['Timestamp'], format='%Y-%m-%d %H:%M:%S.%f')

    fmg_df = pd.read_csv(global_fmg_file_path, parse_dates=['Timestamp'])
    glove_df = pd.read_csv(glove_file_path, parse_dates=['Timestamp'])


    	
    emg_df = resolve_duplicates(emg_df, column='Timestamp')
    aux_df = resolve_duplicates(aux_df, column='Timestamp')
    fmg_df = resolve_duplicates(fmg_df, column='Timestamp')


    # Determine the common time range across all datasets (use the EMG range here)
    start_time = emg_df['Timestamp'].min()
    end_time = emg_df['Timestamp'].max()

    # Filter the other datasets to the same time range as the EMG data
    aux_df = aux_df[(aux_df['Timestamp'] >= start_time) & (aux_df['Timestamp'] <= end_time)]
    fmg_df = fmg_df[(fmg_df['Timestamp'] >= start_time) & (fmg_df['Timestamp'] <= end_time)]
    glove_df = glove_df[(glove_df['Timestamp'] >= start_time) & (glove_df['Timestamp'] <= end_time)]

    # Interpolate AUX data to match EMG timestamps
    aux_df = aux_df.set_index('Timestamp').reindex(emg_df['Timestamp']).interpolate(method='linear').bfill()
    aux_df = aux_df.reset_index().rename(columns={'index': 'Timestamp'})

    # Interpolate glove data to match EMG timestamps
    glove_df = glove_df.set_index('Timestamp').reindex(emg_df['Timestamp']).interpolate(method='linear').bfill()
    glove_df = glove_df.reset_index().rename(columns={'index': 'Timestamp'})

    # Interpolate FMG data to match EMG timestamps
    fmg_df = fmg_df.set_index('Timestamp').reindex(emg_df['Timestamp']).interpolate(method='linear').bfill()
    fmg_df = fmg_df.reset_index().rename(columns={'index': 'Timestamp'})

    emg_df['Timestamp_numeric'] = (emg_df['Timestamp'] - start_time).dt.total_seconds()
    aux_df['Timestamp_numeric'] = (aux_df['Timestamp'] - start_time).dt.total_seconds()
    fmg_df['Timestamp_numeric'] = (fmg_df['Timestamp'] - start_time).dt.total_seconds()
    glove_df['Timestamp_numeric'] = (glove_df['Timestamp'] - start_time).dt.total_seconds()
    
    # Merge all datasets with EMG data using EMG timestamps as the main reference
    integrated_df = pd.merge_asof(emg_df.sort_values('Timestamp'), aux_df.sort_values('Timestamp'), on='Timestamp', suffixes=('', '_aux'))
    integrated_df = pd.merge_asof(integrated_df, fmg_df.sort_values('Timestamp'), on='Timestamp', suffixes=('', '_fmg'))
    integrated_df = pd.merge_asof(integrated_df, glove_df.sort_values('Timestamp'), on='Timestamp', suffixes=('', '_glove'))

    # Rename columns to clarify data sources
    new_columns = {}
    for col in integrated_df.columns:
        if col.endswith('_aux'):
            new_columns[col] = f"Aux_{col[:-4]}"
        elif col.endswith('_fmg'):
            new_columns[col] = f"Fmg_{col[:-4]}"
    integrated_df.rename(columns=new_columns, inplace=True)

    # Drop rows with missing FMG data
    integrated_df = integrated_df.dropna(subset=[col for col in integrated_df.columns if col.startswith('Fmg_')])

    # Rearrange columns if necessary
    cols_to_move = ['Action_Label'] if 'Action_Label' in integrated_df.columns else []
    cols = [col for col in integrated_df.columns if col not in cols_to_move] + cols_to_move
    integrated_df = integrated_df[cols]

    # Create the NumPy arrays from the DataFrame
    labels = integrated_df['Action_Label'].to_numpy(dtype=np.int32).reshape(-1, 1)
    frequ =  np.full((1, 1), 2000)
    repetitions = np.full(len(integrated_df), repetition_value, dtype=np.int32).reshape(-1, 1)

    # EMG data
    emg_data = integrated_df[[sensor for sensor in sensor_list if sensor in integrated_df.columns and sensor != excluded_sensor]].to_numpy(dtype=np.float32)

    # Accelerometer and gyroscope data (general sensors)
    acc_columns = [f"{sensor}_acc_{axis} (g)" for sensor in sensor_list if sensor != excluded_sensor for axis in ['x', 'y', 'z']]
    gyro_columns = [f"{sensor}_gyr_{axis} (deg/s)" for sensor in sensor_list if sensor != excluded_sensor for axis in ['x', 'y', 'z']]
    acc_data = integrated_df[acc_columns].to_numpy(dtype=np.float32) if acc_columns else np.empty((len(integrated_df), 0), dtype=np.float32)
    gyro_data = integrated_df[gyro_columns].to_numpy(dtype=np.float32) if gyro_columns else np.empty((len(integrated_df), 0), dtype=np.float32)

    # Accelerometer and gyroscope data (excluded sensor)
    glove_acc_data = integrated_df[[f"{excluded_sensor}_acc_{axis} (g)" for axis in ['x', 'y', 'z']]].to_numpy(dtype=np.float32) \
        if f"{excluded_sensor}_acc_x (g)" in integrated_df.columns else np.empty((len(integrated_df), 0), dtype=np.float32)
    glove_gyro_data = integrated_df[[f"{excluded_sensor}_gyr_{axis} (deg/s)" for axis in ['x', 'y', 'z']]].to_numpy(dtype=np.float32) \
        if f"{excluded_sensor}_gyr_x (deg/s)" in integrated_df.columns else np.empty((len(integrated_df), 0), dtype=np.float32)

    # FMG data
    fmg_columns = [f"FSR{i:02d}" for i in range(1, 25) if f"FSR{i:02d}" in integrated_df.columns]
    fmg_data = integrated_df[fmg_columns].to_numpy(dtype=np.float32) if fmg_columns else np.empty((len(integrated_df), 0), dtype=np.float32)

    # Glove data
    glove_columns = [f"Sensor{i}" for i in range(18) if f"Sensor{i}" in integrated_df.columns]
    glove_data = integrated_df[glove_columns].to_numpy(dtype=np.float32) if glove_columns else np.empty((len(integrated_df), 0), dtype=np.float32)



    timestamp_data = integrated_df['Timestamp_numeric'].to_numpy(dtype=np.float32).reshape(-1, 1)

    # Combine data into a dictionary
    data_dict = {
        'frequency': frequ,
        'repetition': repetitions,
        'stimulus': labels,
        'emg': emg_data,
        'acc': acc_data,
        'gyro': gyro_data,
        'fmg': fmg_data,
        'glove': glove_data,
        'glove_acc': glove_acc_data,
        'glove_gyro': glove_gyro_data,
        'timestamp': timestamp_data,  # Add numeric timestamps
    }

    # Save as .mat file
    savemat(output_file_path, data_dict)
    print(f"Data integration and conversion completed. File saved to {output_file_path}.")







def data_integration_and_mat_conversion(
    global_emg_file_path,
    global_aux_file_path,
    global_fmg_file_path,
    glove_file_path,
    output_mat_file_path,
    sensor_list,
    repetition_value
):
    # Load CSV files
    emg_df = pd.read_csv(global_emg_file_path, dtype={'Timestamp': 'object'})
    emg_df['Timestamp'] = pd.to_datetime(emg_df['Timestamp'], format='%Y-%m-%d %H:%M:%S.%f')

    aux_df = pd.read_csv(global_aux_file_path, parse_dates=['Timestamp'])
    fmg_df = pd.read_csv(global_fmg_file_path, parse_dates=['Timestamp'])
    glove_df = pd.read_csv(glove_file_path, parse_dates=['Timestamp'])

    # Remove columns with only 0.0
    emg_df = emg_df.loc[:, (emg_df != 0.0).any(axis=0)]
    aux_df = aux_df.loc[:, (aux_df != 0.0).any(axis=0)]

    # Ensure all dataframes are sorted by timestamp (required for merge_asof)
    emg_df = emg_df.sort_values('Timestamp')
    aux_df = aux_df.sort_values('Timestamp')
    fmg_df = fmg_df.sort_values('Timestamp')
    glove_df = glove_df.sort_values('Timestamp')

    emg_df.columns = [
        f"EMG{col}" if col not in ['Timestamp', 'Action_Label'] else col
        for col in emg_df.columns
    ]

    # Umbenennen der Spalten in aux_df, außer 'Timestamp' und 'Action_Label'
    aux_df.columns = [
        f"AUX{col}" if col not in ['Timestamp', 'Action_Label'] else col
        for col in aux_df.columns
]

    # Merge using nearest timestamp alignment
    integrated_df = pd.merge_asof(emg_df, aux_df, on='Timestamp', suffixes=('', ''))
    integrated_df = pd.merge_asof(integrated_df, fmg_df, on='Timestamp', suffixes=('', '_fmg'))
    integrated_df = pd.merge_asof(integrated_df, glove_df, on='Timestamp', suffixes=('', '_glove'))

    # Convert timestamps to numeric (relative to start_time)
    start_time = integrated_df['Timestamp'].min()
    integrated_df['Timestamp_numeric'] = (integrated_df['Timestamp'] - start_time).dt.total_seconds()

    # Extract numerical data
    labels = integrated_df['Action_Label'].to_numpy(dtype=np.int32).reshape(-1, 1)
    timestamp_data = integrated_df['Timestamp_numeric'].to_numpy(dtype=np.float32).reshape(-1, 1)

    # Drop non-numeric columns before converting to NumPy
    emg_data = integrated_df.filter(regex='EMG\d+', axis=1).to_numpy(dtype=np.float32)
    aux_data = integrated_df.filter(regex='AUX\d+', axis=1).to_numpy(dtype=np.float32)
    fmg_data = integrated_df.filter(regex='FSR\d+', axis=1).to_numpy(dtype=np.float32)
    glove_data = integrated_df.filter(regex='Sensor\d+', axis=1).to_numpy(dtype=np.float32)
    


    # Split AUX into ACC and GYRO (assuming groups of 6 columns)
    acc_data = np.hstack([aux_data[:, i:i+3] for i in range(0, aux_data.shape[1], 6)])
    gyro_data = np.hstack([aux_data[:, i+3:i+6] for i in range(0, aux_data.shape[1], 6)])

    # Move first few columns to the end for correct alignment
    emg_data = np.hstack([emg_data[:, 4:], emg_data[:, :4]])
    gyro_data = np.hstack([gyro_data[:, 3:], gyro_data[:, :3]])
    acc_data = np.hstack([acc_data[:, 3:], acc_data[:, :3]])

    # Create dictionary for .mat file
    data_dict = {
        'frequency': np.full((1, 1), 2000),
        'repetition': np.full(len(integrated_df), repetition_value, dtype=np.int32).reshape(-1, 1),
        'stimulus': labels, #+17
        'emg': emg_data,
        'gyro': gyro_data,
        'acc': acc_data,
        'fmg': fmg_data,
        'glove': glove_data,
        'timestamp': timestamp_data,
    }

    # Save as .mat file
    savemat(output_mat_file_path, data_dict)
    print(f"Data integration and conversion completed. File saved to {output_mat_file_path}.")




def merge_mat_files(base_folder, final_output_file, interpolated_output_file):
    """
    Merges all 'final_data_*.mat' files and 'interpolated_data_*.mat' files 
    in subfolders of a specified folder into two separate .mat files.
    
    Parameters:
    - base_folder: str, path to the base folder containing subfolders with .mat files.
    - final_output_file: str, path to the output .mat file for merged final_data files.
    - interpolated_output_file: str, path to the output .mat file for merged interpolated_data files.
    
    Output:
    Saves the merged data as two separate .mat files.
    """
    final_data = {}
    interpolated_data = {}
    
    # Initialize flags for keys in the merged data
    final_keys_initialized = False
    interpolated_keys_initialized = False
    
    # Recursively find all .mat files in subfolders
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.endswith('.mat'):
                mat_path = os.path.join(root, file)
                print(f"Processing: {mat_path}")

                # Load the .mat file
                mat_data = loadmat(mat_path)
                
                # Determine if the file is a final_data file or interpolated_data file
                if 'final_data' in file:
                    # Merge final_data files
                    final_id = file.split('_')[-1].replace(".mat", "")
                    if not final_keys_initialized:
                        # Initialize merged_data with keys from the first final_data file
                        for key in mat_data:
                            # Skip metadata fields
                            if not key.startswith('__'):
                                final_data[key] = mat_data[key]
                        final_keys_initialized = True
                    else:
                        # Merge data for each key in final_data
                        final_int_id = file.split('_')[-1].replace(".mat", "")
                        for key in final_data.keys():
                            if key in mat_data:
                                # Concatenate arrays for final_data
                                if isinstance(final_data[key], np.ndarray) and isinstance(mat_data[key], np.ndarray):
                                    final_data[key] = np.vstack((final_data[key], mat_data[key]))
                                else:
                                    print(f"Warning: Skipping concatenation for non-array key '{key}' in final_data.")
                            else:
                                print(f"Warning: Key '{key}' not found in file {file}. Skipping.")
                
                elif 'interpolated_data' in file:
                    # Merge interpolated_data files
                    if not interpolated_keys_initialized:
                        # Initialize merged_data with keys from the first interpolated_data file
                        for key in mat_data:
                            # Skip metadata fields
                            if not key.startswith('__'):
                                interpolated_data[key] = mat_data[key]
                        interpolated_keys_initialized = True
                    else:
                        # Merge data for each key in interpolated_data
                        for key in interpolated_data.keys():
                            if key in mat_data:
                                # Concatenate arrays for interpolated_data
                                if isinstance(interpolated_data[key], np.ndarray) and isinstance(mat_data[key], np.ndarray):
                                    interpolated_data[key] = np.vstack((interpolated_data[key], mat_data[key]))
                                else:
                                    print(f"Warning: Skipping concatenation for non-array key '{key}' in interpolated_data.")
                            else:
                                print(f"Warning: Key '{key}' not found in file {file}. Skipping.")
    
    # Save the merged final_data to the output file
    if final_data:
        # Erstelle den finalen Dateipfad mit final_id
        final_output_file = final_output_file + "_" + final_id + ".mat"

        # Extrahiere den Ordnerpfad aus dem finalen Dateipfad
        output_dir = os.path.dirname(final_output_file)

        # Prüfe, ob der Ordner existiert, und erstelle ihn bei Bedarf
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Ordner {output_dir} wurde erstellt.")

        # Speichere die finalen Daten als .mat-Datei
        savemat(final_output_file, final_data)
        print(f"Merged final_data saved to {final_output_file}")
    else:
        print("No final_data files were found to merge.")
    
    # Save the merged interpolated_data to the output file
    if interpolated_data:
        interpolated_output_file=interpolated_output_file+"_"+ final_int_id+".mat"
        savemat(interpolated_output_file, interpolated_data)
        print(f"Merged interpolated_data saved to {interpolated_output_file}")
    else:
        print("No interpolated_data files were found to merge.")




def resolve_duplicates(df, column='Timestamp'):
    # Find duplicates
    duplicates = df[df[column].duplicated(keep=False)]
    if not duplicates.empty:
        print(f"Resolving duplicates for {len(duplicates)} rows")
        print(duplicates[column].value_counts())

    # Add a small time delta to each duplicate
    df[column] += pd.to_timedelta(df.groupby(column).cumcount() * 1e-6, unit='s')

    # Verify uniqueness
    if df[column].duplicated().any():
        print("Duplicates still exist after resolution!")
    else:
        print("Duplicates successfully resolved.")
    return df

def mat_and_cuttoff(
    global_emg_file_path,
    global_aux_file_path,
    global_fmg_file_path,
    glove_file_path,
    output_mat_file_path,
    repetition_value,
    cutoff_label
):
    # Load the CSV files and parse timestamps
    emg_df = pd.read_csv(global_emg_file_path, dtype={'Timestamp': 'object'})
    emg_df['Timestamp'] = pd.to_datetime(emg_df['Timestamp'], format='%Y-%m-%d %H:%M:%S.%f')

    aux_df = pd.read_csv(global_aux_file_path, parse_dates=['Timestamp'])
    fmg_df = pd.read_csv(global_fmg_file_path, parse_dates=['Timestamp'])
    glove_df = pd.read_csv(glove_file_path, parse_dates=['Timestamp'])

    # Remove columns in EMG and AUX that contain only 0.0
    emg_df = emg_df.loc[:, (emg_df != 0.0).any(axis=0)]
    aux_df = aux_df.loc[:, (aux_df != 0.0).any(axis=0)]

    # Synchronize timestamps by defining a common time range
    start_time = max(
        emg_df['Timestamp'].min(),
        aux_df['Timestamp'].min(),
        fmg_df['Timestamp'].min(),
        glove_df['Timestamp'].min()
    )
    end_time = min(
        emg_df['Timestamp'].max(),
        aux_df['Timestamp'].max(),
        fmg_df['Timestamp'].max(),
        glove_df['Timestamp'].max()
    )

    # Filter data based on synchronized timestamps
    emg_df = emg_df[(emg_df['Timestamp'] >= start_time) & (emg_df['Timestamp'] <= end_time)]
    aux_df = aux_df[(aux_df['Timestamp'] >= start_time) & (aux_df['Timestamp'] <= end_time)]
    fmg_df = fmg_df[(fmg_df['Timestamp'] >= start_time) & (fmg_df['Timestamp'] <= end_time)]
    glove_df = glove_df[(glove_df['Timestamp'] >= start_time) & (glove_df['Timestamp'] <= end_time)]

    if cutoff_label in emg_df['Action_Label'].values:
        cutoff_time = emg_df[emg_df['Action_Label'] == cutoff_label]['Timestamp'].max()
        
        # Nur Werte behalten, die VOR dem letzten Auftreten des Labels liegen
        emg_df = emg_df[emg_df['Timestamp'] <= cutoff_time]
        aux_df = aux_df[aux_df['Timestamp'] <= cutoff_time]
        fmg_df = fmg_df[fmg_df['Timestamp'] <= cutoff_time]
        glove_df = glove_df[glove_df['Timestamp'] <= cutoff_time]

    # Convert timestamps to numeric (seconds since start_time)
    emg_df['Timestamp_numeric'] = (emg_df['Timestamp'] - start_time).dt.total_seconds()
    aux_df['Timestamp_numeric'] = (aux_df['Timestamp'] - start_time).dt.total_seconds()
    fmg_df['Timestamp_numeric'] = (fmg_df['Timestamp'] - start_time).dt.total_seconds()
    glove_df['Timestamp_numeric'] = (glove_df['Timestamp'] - start_time).dt.total_seconds()

    # Convert data to NumPy arrays
    emg_data = emg_df.select_dtypes(include=[np.number]).to_numpy(dtype=np.float32)
    aux_data = aux_df.select_dtypes(include=[np.number]).to_numpy(dtype=np.float32)
    fmg_data = fmg_df.select_dtypes(include=[np.number]).to_numpy(dtype=np.float32)
    glove_data = glove_df.select_dtypes(include=[np.number]).to_numpy(dtype=np.float32)


    labels = emg_df['Action_Label'].to_numpy(dtype=np.int32).reshape(-1, 1)
    timestamp_data = emg_df['Timestamp_numeric'].to_numpy(dtype=np.float32).reshape(-1, 1)


    emg_df = emg_df.sort_values('Timestamp')
    aux_df = aux_df.sort_values('Timestamp')
    fmg_df = fmg_df.sort_values('Timestamp')
    glove_df = glove_df.sort_values('Timestamp')

    emg_df.columns = [
        f"EMG{col}" if col not in ['Timestamp', 'Action_Label'] else col
        for col in emg_df.columns
    ]

    # Umbenennen der Spalten in aux_df, außer 'Timestamp' und 'Action_Label'
    aux_df.columns = [
        f"AUX{col}" if col not in ['Timestamp', 'Action_Label'] else col
        for col in aux_df.columns
]

    # Merge using nearest timestamp alignment
    integrated_df = pd.merge_asof(emg_df, aux_df, on='Timestamp', suffixes=('', ''))
    integrated_df = pd.merge_asof(integrated_df, fmg_df, on='Timestamp', suffixes=('', '_fmg'))
    integrated_df = pd.merge_asof(integrated_df, glove_df, on='Timestamp', suffixes=('', '_glove'))

    # Convert timestamps to numeric (relative to start_time)
    start_time = integrated_df['Timestamp'].min()
    integrated_df['Timestamp_numeric'] = (integrated_df['Timestamp'] - start_time).dt.total_seconds()

    # Extract numerical data
    labels = integrated_df['Action_Label'].to_numpy(dtype=np.int32).reshape(-1, 1)
    timestamp_data = integrated_df['Timestamp_numeric'].to_numpy(dtype=np.float32).reshape(-1, 1)

    # Drop non-numeric columns before converting to NumPy
    emg_data = integrated_df.filter(regex='EMG\d+', axis=1).to_numpy(dtype=np.float32)
    aux_data = integrated_df.filter(regex='AUX\d+', axis=1).to_numpy(dtype=np.float32)
    fmg_data = integrated_df.filter(regex='FSR\d+', axis=1).to_numpy(dtype=np.float32)
    glove_data = integrated_df.filter(regex='Sensor\d+', axis=1).to_numpy(dtype=np.float32)
    


    # Split AUX into ACC and GYRO (assuming groups of 6 columns)
    acc_data = np.hstack([aux_data[:, i:i+3] for i in range(0, aux_data.shape[1], 6)])
    gyro_data = np.hstack([aux_data[:, i+3:i+6] for i in range(0, aux_data.shape[1], 6)])

    # Move first few columns to the end for correct alignment
    emg_data = np.hstack([emg_data[:, 4:], emg_data[:, :4]])
    gyro_data = np.hstack([gyro_data[:, 3:], gyro_data[:, :3]])
    acc_data = np.hstack([acc_data[:, 3:], acc_data[:, :3]])

    # Create dictionary for .mat file
    data_dict = {
        'frequency': np.full((1, 1), 2000),
        'repetition': np.full(len(integrated_df), 6, dtype=np.int32).reshape(-1, 1),
        'stimulus': labels,
        'emg': emg_data,
        'gyro': gyro_data,
        'acc': acc_data,
        'fmg': fmg_data,
        'glove': glove_data,
        'timestamp': timestamp_data,
    }

    # Save as .mat file
    savemat(output_mat_file_path, data_dict)
    print(f"Data integration and conversion completed. File saved to {output_mat_file_path}.")



def new_cut(
    global_emg_file_path,
    global_aux_file_path,
    global_fmg_file_path,
    glove_file_path,
    output_mat_file_path,
    repetition_value,
    cutoff  # New parameter
):
    # Load CSV files
    emg_df = pd.read_csv(global_emg_file_path, dtype={'Timestamp': 'object'})
    emg_df['Timestamp'] = pd.to_datetime(emg_df['Timestamp'], format='%Y-%m-%d %H:%M:%S.%f')

    aux_df = pd.read_csv(global_aux_file_path, parse_dates=['Timestamp'])
    fmg_df = pd.read_csv(global_fmg_file_path, parse_dates=['Timestamp'])
    glove_df = pd.read_csv(glove_file_path, parse_dates=['Timestamp'])

    # Remove columns with only 0.0
    emg_df = emg_df.loc[:, (emg_df != 0.0).any(axis=0)]
    aux_df = aux_df.loc[:, (aux_df != 0.0).any(axis=0)]

    # Ensure all dataframes are sorted by timestamp
    emg_df = emg_df.sort_values('Timestamp')
    aux_df = aux_df.sort_values('Timestamp')
    fmg_df = fmg_df.sort_values('Timestamp')
    glove_df = glove_df.sort_values('Timestamp')

    emg_df.columns = [
        f"EMG{col}" if col not in ['Timestamp', 'Action_Label'] else col
        for col in emg_df.columns
    ]

    aux_df.columns = [
        f"AUX{col}" if col not in ['Timestamp', 'Action_Label'] else col
        for col in aux_df.columns
    ]

    # Merge using nearest timestamp alignment
    integrated_df = pd.merge_asof(emg_df, aux_df, on='Timestamp', suffixes=('', ''))
    integrated_df = pd.merge_asof(integrated_df, fmg_df, on='Timestamp', suffixes=('', '_fmg'))
    integrated_df = pd.merge_asof(integrated_df, glove_df, on='Timestamp', suffixes=('', '_glove'))

    # Convert timestamps to numeric (relative to start_time)
    start_time = integrated_df['Timestamp'].min()
    integrated_df['Timestamp_numeric'] = (integrated_df['Timestamp'] - start_time).dt.total_seconds()

    # Extract numerical data
    labels = integrated_df['Action_Label'].to_numpy(dtype=np.int32).reshape(-1, 1)
    timestamp_data = integrated_df['Timestamp_numeric'].to_numpy(dtype=np.float32).reshape(-1, 1)

    # Find last occurrence of cutoff stimulus
    last_cutoff_index = np.where(labels == cutoff)[0]
    if len(last_cutoff_index) > 0:
        last_cutoff_index = last_cutoff_index[-1]  # Last occurrence of cutoff
    else:
        last_cutoff_index = len(labels)  # If cutoff is not found, keep all data

    # Drop non-numeric columns before converting to NumPy
    emg_data = integrated_df.filter(regex='EMG\d+', axis=1).to_numpy(dtype=np.float32)[:last_cutoff_index + 1]
    aux_data = integrated_df.filter(regex='AUX\d+', axis=1).to_numpy(dtype=np.float32)[:last_cutoff_index + 1]
    fmg_data = integrated_df.filter(regex='FSR\d+', axis=1).to_numpy(dtype=np.float32)[:last_cutoff_index + 1]
    glove_data = integrated_df.filter(regex='Sensor\d+', axis=1).to_numpy(dtype=np.float32)[:last_cutoff_index + 1]
    labels = labels[:last_cutoff_index + 1]
    timestamp_data = timestamp_data[:last_cutoff_index + 1]

    # Split AUX into ACC and GYRO (assuming groups of 6 columns)
    acc_data = np.hstack([aux_data[:, i:i+3] for i in range(0, aux_data.shape[1], 6)])
    gyro_data = np.hstack([aux_data[:, i+3:i+6] for i in range(0, aux_data.shape[1], 6)])

    # Move first few columns to the end for correct alignment
    emg_data = np.hstack([emg_data[:, 4:], emg_data[:, :4]])
    gyro_data = np.hstack([gyro_data[:, 3:], gyro_data[:, :3]])
    acc_data = np.hstack([acc_data[:, 3:], acc_data[:, :3]])

    # Create dictionary for .mat file
    data_dict = {
        'frequency': np.full((1, 1), 2000),
        'repetition': np.full(len(labels), repetition_value, dtype=np.int32).reshape(-1, 1),
        'stimulus': labels,
        'emg': emg_data,
        'gyro': gyro_data,
        'acc': acc_data,
        'fmg': fmg_data,
        'glove': glove_data,
        'timestamp': timestamp_data,
    }

    # Save as .mat file
    savemat(output_mat_file_path, data_dict)
    print(f"Data integration and conversion completed. File saved to {output_mat_file_path}.")
