import os
from aux_data import aux_data_processing
from emg_data import emg_data_processing_upsampling
from fmg_data import fmg_data_processing
from data_integration import data_integration_processing_interpolate, data_integration_and_mat_conversion,merge_mat_files,mat_and_cuttoff
import scipy
import numpy as np
from scipy.io import loadmat, savemat


def merge_2_mat_files(mat_file_path1, mat_file_path2, output_file_path):
    # Load both .mat files
    data1 = scipy.io.loadmat(mat_file_path1)
    data2 = scipy.io.loadmat(mat_file_path2)

    # Ensure 'timestamp' exists in both files
    if 'timestamp' in data1 and 'timestamp' in data2:
        data2['timestamp'] += np.max(data1['timestamp']) + 5e-4  # Add a small offset (e.g., 1e-6)


    # Merge all relevant data arrays
    keys_to_merge = ['stimulus', 'emg', 'gyro', 'acc', 'fmg', 'glove', 'timestamp', 'repetition']
    
    merged_data = {}
    for key in keys_to_merge:
        if key in data1 and key in data2:
            merged_data[key] = np.vstack([data1[key], data2[key]])

    if 'frequency' not in  merged_data:
         merged_data['frequency'] = np.array([2000])  
    # Save the merged data to a new .mat file
    scipy.io.savemat(output_file_path, merged_data)
    print(f"Merged .mat file saved to {output_file_path}")




def process_all_participants(input_base_folder, processing_base_folder, output_base_folder,sensors):
    # Iterate through the numeric subfolders in the input base folder
    for test_order in os.listdir(input_base_folder):
        test_order_path = os.path.join(input_base_folder, test_order)
        
        # Ensure the folder name is numeric and it is a directory
        if os.path.isdir(test_order_path) and test_order.isdigit():
            # Create corresponding folders in processing and output
            processing_folder = os.path.join(processing_base_folder, test_order)
            output_folder = os.path.join(output_base_folder, test_order)
            os.makedirs(processing_folder, exist_ok=True)
            os.makedirs(output_folder, exist_ok=True)

            # Process the files in this test order folder
            process_files_in_test_order(test_order_path, processing_folder, output_folder, test_order,sensors)
        


def process_files_in_test_order(test_order_path, processing_folder, output_folder, test_order,sensors):
    # Collect participant numbers by matching file names
    participants = set()
    for file_name in os.listdir(test_order_path):
        if file_name.startswith('emg_data_P') and file_name.endswith('.csv'):
            participant_num = file_name.split('_P')[1].split('.')[0]  # Extract participant number
            participants.add(participant_num)

    # Process each participant's files
    for participant_num in participants:
        # Define file paths for each data type
        input_emg_file = os.path.join(test_order_path, f'emg_data_P{participant_num}.csv')
        input_aux_file = os.path.join(test_order_path, f'aux_data_P{participant_num}.csv')
        input_fmg_file = os.path.join(test_order_path, f'fmg_data_P{participant_num}.csv')
        input_glove_file = os.path.join(test_order_path, f'glove_data_P{participant_num}.csv')

        # Ensure all required files exist for this participant
        if not (os.path.exists(input_emg_file) and os.path.exists(input_aux_file) and 
                os.path.exists(input_fmg_file) and os.path.exists(input_glove_file)):
            print(f"Skipping participant {participant_num} in test order {test_order}: Missing required files.")
            continue

        # Define intermediate and final output file paths
        output_emg_file = os.path.join(processing_folder, f'emg_data_P{participant_num}_m.csv')
        output_aux_file = os.path.join(processing_folder, f'aux_data_P{participant_num}_m.csv')
        output_fmg_file = os.path.join(processing_folder, f'fmg_data_P{participant_num}_m.csv')
        
        final_output_file = os.path.join(output_folder, f'final_data_P{participant_num}.mat')
        final_output_file_int = os.path.join(output_folder, f'interpolated_data_P{participant_num}.mat')
        final_output_file_cut = os.path.join(output_folder, f'cutted_data_P{participant_num}.mat')
        # Perform the processing
        try:
            print(f"Processing participant {participant_num} in test order {test_order}...")

            # Step 1: Process EMG, AUX, and FMG data
            emg_data_processing_upsampling(input_emg_file, output_emg_file)
            aux_data_processing(input_aux_file, output_aux_file)
            fmg_data_processing(input_fmg_file, input_emg_file, output_fmg_file)

            # Step 2: Integrate data
            repetition_value=test_order
            data_integration_and_mat_conversion(output_emg_file, output_aux_file, output_fmg_file, input_glove_file, final_output_file,sensors,repetition_value)
           # data_integration_processing_interpolate(output_emg_file, output_aux_file, output_fmg_file, input_glove_file, final_output_file_int,sensors,repetition_value)
            #mat_and_cuttoff(output_emg_file, output_aux_file, output_fmg_file, input_glove_file, final_output_file_cut,repetition_value,cut_off)

            print(f"Completed processing for participant {participant_num} in test order {test_order}.")
            print(f"Completed processing for participant {participant_num} in test order {test_order}.")

            
    
        except Exception as e:
            print(f"Error processing participant {participant_num} in test order {test_order}: {e}")



# Load the saved .mat file
def cut_mat(input,output,cutoff):
        data = loadmat(input)

        # Find last occurrence of the cutoff stimulus
        new_repetition_value=Folder
        labels = data['stimulus']
        
        last_cutoff_index = np.where(labels == cutoff)[0]
        if len(last_cutoff_index) > 0:
            last_cutoff_index = last_cutoff_index[-1]  # Last occurrence
        else:
            last_cutoff_index = len(labels)  # Keep all data if cutoff not found

        # Cut all relevant data fields
        for key in ['stimulus', 'emg', 'gyro', 'acc', 'fmg', 'glove', 'timestamp', 'repetition']:
            if key in data:
                data[key] = data[key][:last_cutoff_index + 1]

        if 'repetition' in data :
            data['repetition'] = np.full_like(data['repetition'], new_repetition_value, dtype=np.int32)

        # Save the trimmed data back to a new .mat file
        savemat(output, data)
        print("Trimmed .mat file saved.")
        



cut_off=61
Folder=4
Pat=34
if __name__ == "__main__":

    input_base_folder = f'../data/input_data/P{Pat}'  # Input data folder with test order subfolders
    processing_base_folder = f'../data/processing_data/P{Pat}'  # Folder for intermediate processing files
    output_base_folder = f'../data/output_data/P{Pat}'  # Folder for final output files
    sensors=['S1','S2','S3','S4','S5','S6','S7','S8'] # Number of all used Sensores

    final_data = f'../data/final_data/P{Pat}/final_data'  # Base output folder
    interpolated_output_file=f'../data/final_data/P{Pat}/final_interpolated_data'

    # Creates 2 Files (interpolated and not ) for every participant

    process_all_participants(input_base_folder, processing_base_folder, output_base_folder,sensors)
   

    if 0: # cutting data
        mat_file_path1=f'../data/output_data/P{Pat}/{Folder}00{cut_off}/final_data_P{Pat}.mat' # first half (cutted)
        output_file_path=f'../data/output_data/P{Pat}/{Folder}/final_data_P{Pat}_done.mat'# final file
        cut_mat( mat_file_path1,output_file_path,cut_off)
        
        output_file_path=f'../data/output_data/P{Pat}/{Folder}/final_data_P{Pat}_done.mat'# final file
        mat_file_path2=f'../data/output_data/P{Pat}/{Folder}/final_data_P{Pat}.mat' # rest
       
        output_file_path2=f'../data/output_data/P{Pat}/{Folder}/final_data_P{Pat}_f.mat'# final file

        merge_2_mat_files(output_file_path,mat_file_path2, output_file_path2)
  



    merge_mat_files(output_base_folder,final_data, interpolated_output_file)

 