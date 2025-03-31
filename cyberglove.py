import numpy as np
import struct
import serial
import serial.tools.list_ports

def load_calibration(cal_path, n_df):
    """
    Reads a CyberGlove calibration file and returns offset and gain values.
    Gains are converted from radians to degrees.

    Parameters
    ----------
    cal_path : string
        Path to the calibration file.
    n_df : int
        Number of degrees of freedom (DOF) in the CyberGlove model (either 18 or 22).

    Returns
    -------
    offset : np.array, shape=(n_df,)
        Array of sensor offsets for calibration.
    gain : np.array, shape=(n_df,)
        Array of sensor gains for calibration.
    """
    # Open the calibration file and read all lines
    f = open(cal_path, 'r')
    lines = f.readlines()

    # Define index mappings based on CyberGlove model (18-DOF or 22-DOF)
    if n_df == 18:
        lines_idx_offset = [2, 3, 4, 5, 7, 8, 12, 13, 15, 17, 18, 20, 22, 23, 25, 27, 28, 29]
        lines_idx_gain = [2, 3, 4, 5, 7, 8, 12, 13, 10, 17, 18, 20, 22, 23, 25, 27, 28, 29]
    elif n_df == 22:
        lines_idx_offset = [2, 3, 4, 5, 7, 8, 9, 12, 13, 14, 15, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29]
        lines_idx_gain = [2, 3, 4, 5, 7, 8, 9, 12, 13, 14, 10, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29]
    else:
        raise ValueError("CyberGlove can be either 18-DOF or 22-DOF.")

    # Read the offset and gain values from specified lines in the file
    offset = []
    gain = []
    for line in lines_idx_offset:
        offset.append(-float(lines[line].split(' ')[6]))  # Negate offset value as specified
    for line in lines_idx_gain:
        gain.append(float(lines[line].split(' ')[9]) * (180 / np.pi))  # Convert gains from radians to degrees

    # Convert lists to numpy arrays
    offset = np.asarray(offset)
    gain = np.asarray(gain)
    return (offset, gain)

def calibrate_data(data, offset, gain):
    """
    Applies calibration to raw CyberGlove data.

    Parameters
    ----------
    data : np.array, shape=(n_df,)
        Raw sensor data from the CyberGlove.
    offset : np.array, shape=(n_df,)
        Offset values for calibration.
    gain : np.array, shape=(n_df,)
        Gain values for calibration.

    Returns
    -------
    np.array, shape=(n_df,)
        Calibrated sensor data.
    """
    # Apply gain and offset to calibrate the data
    return data * gain + offset

class CyberGlove(object):
    """
    Interface class for CyberGlove with serial communication.

    Parameters
    ----------
    n_df : int
        Number of degrees of freedom (DOF) in the CyberGlove model (18 or 22).
    s_port : str, optional
        Serial port name (default: first available port).
    baud_rate : int, optional
        Baud rate for serial communication (default: 115200).
    samples_per_read : int, optional
        Number of samples per read cycle (default: 1).
    cal_path : str, optional
        Path to the calibration file (default: None).
    """

    def __init__(self, n_df, s_port=None, baud_rate=115200, samples_per_read=1, cal_path=None):
        # Use first available serial port if none specified
        if s_port is None:
            try:
                s_port = serial.tools.list_ports.comports()[0].device
            except StopIteration:
                print("No serial ports found.")

        # Store parameters
        self.n_df = n_df
        self.s_port = s_port
        self.baud_rate = baud_rate
        self.samples_per_read = samples_per_read
        self.cal_path = cal_path

        # Set number of bytes per read based on CyberGlove model
        if self.n_df == 18:
            self.__bytesPerRead = 20  # Reserved bytes included for 18-DOF model
        elif self.n_df == 22:
            self.__bytesPerRead = 24  # Reserved bytes included for 22-DOF model

        # Initialize serial interface
        self.si = serial.Serial(port=self.s_port, baudrate=self.baud_rate, timeout=1, writeTimeout=1)

        # Load calibration if file path provided
        if self.cal_path is None:
            self.calibration_ = False
        else:
            self.calibration_ = True
            (self.cal_offset_, self.cal_gain_) = load_calibration(self.cal_path, self.n_df)

    def __del__(self):
        """Destructor calls stop() to ensure port is closed."""
        self.stop()

    def start(self):
        """Open the serial port and flush buffers."""
        if not self.si.is_open:
            self.si.open()
            self.si.flushOutput()
            self.si.flushInput()

    def stop(self):
        """Close the serial port after flushing buffers."""
        if self.si.is_open:
            self.si.flushInput()
            self.si.flushOutput()
            self.si.close()

    def read(self):
        """
        Reads data samples from the CyberGlove.

        Returns
        -------
        data : np.array, shape=(n_df, samples_per_read)
            Sensor data with each row representing a sensor and each column a time sample.
        """
        # Format for unpacking byte data
        fmt = '@' + "B" * self.__bytesPerRead
        data = np.zeros((self.n_df, self.samples_per_read))  # Initialize array to store data

        # Read specified number of samples
        for i in range(self.samples_per_read):
            self.si.flushInput()  # Clear input buffer for fresh data
            raw_data = None

            # Request data until valid data is received
            while raw_data is None:
                nb = self.si.write(bytes('\x47', 'utf'))  # Send request byte
                if nb == 1:  # If 1 byte successfully written
                    msg = self.si.read(size=self.__bytesPerRead)  # Read specified bytes
                    if len(msg) == self.__bytesPerRead:
                        raw_data = struct.unpack(fmt, msg)  # Unpack data from bytes
                        raw_data = np.asarray(raw_data)[1:-1]  # Exclude reserved bytes

                        # Apply calibration if available
                        if self.calibration_:
                            data[:, i] = calibrate_data(raw_data, self.cal_offset_, self.cal_gain_)
                        else:
                            data[:, i] = raw_data

        return data
