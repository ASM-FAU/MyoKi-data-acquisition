import scipy.io
import numpy as np
import matplotlib.pyplot as plt

# Load .mat file
if __name__ == "__main__":
    mat_data = scipy.io.loadmat(f'../data/final_data/P19/final_data_P19')

    # Extract relevant data
    fmg_data = mat_data['fmg']  # FMG data (18 columns for 18 sensors)hnhdf
    glove_data = mat_data['glove']  # Glove data
    stimulus = mat_data['stimulus'].flatten()  # Convert to 1D array if needed
    timestamps = mat_data['timestamp'].flatten()  # Extract timestamp data (numeric)

    # Find the first index where stimulus becomes 1
    stimulus_change_idx = np.where(stimulus == 1)[0][0]

    # Edge detection for FMG and Glove data
    def find_first_edge(data, start_idx):
        """Find the first significant change (edge) after stimulus onset."""
        diff = np.diff(data, axis=0)  # Compute derivative along axis 0 (samples)
        edge_idx = np.argmax(diff[start_idx:]) + start_idx  # Find first max change
        return edge_idx

    fmg_edge_idx = find_first_edge(fmg_data, stimulus_change_idx)
    glove_edge_idx = find_first_edge(glove_data, stimulus_change_idx)

    # Ensure the index is within bounds for the timestamps array
    if fmg_edge_idx >= len(timestamps):
        fmg_edge_idx = len(timestamps) - 1  # Set to last valid index
    if glove_edge_idx >= len(timestamps):
        glove_edge_idx = len(timestamps) - 1  # Set to last valid index

    # Convert indices to timestamps
    fmg_edge_time = timestamps[fmg_edge_idx]
    glove_edge_time = timestamps[glove_edge_idx]

    # Print the results (optional)
    print(f"FMG first edge index: {fmg_edge_idx}")
    print(f"Glove first edge index: {glove_edge_idx}")
    print(f"FMG edge time: {fmg_edge_time}")
    print(f"Glove edge time: {glove_edge_time}")

    # Optional: Plot only the edges
    plt.figure(figsize=(10, 4))
    plt.axvline(fmg_edge_time, color='r', linestyle='--', label="FMG Edge")
    plt.axvline(glove_edge_time, color='g', linestyle='--', label="Glove Edge")
    plt.axvline(timestamps[stimulus_change_idx], color='b', linestyle='--', label="Stimulus Onset")

    # Labels and Title
    plt.xlabel("Time (units)")
    plt.ylabel("Signal")
    plt.legend()
    plt.title("FMG and Glove Data Edge Detection (Only Edges)")

    # Show the plot
    plt.show()
