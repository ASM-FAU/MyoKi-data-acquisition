import socket
import struct
import numpy
from collections import defaultdict
import pandas as pd
import datetime

class _BaseTrignoDaq(object):
    """
    Delsys Trigno wireless EMG system.

    Requires the Trigno Control Utility to be running.

    Parameters
    ----------
    host : str
        IP address the TCU server is running on.
    cmd_port : int
        Port of TCU command messages.
    data_port : int
        Port of TCU data access.
    rate : int
        Sampling rate of the data source.
    total_channels : int
        Total number of channels supported by the device.
    timeout : float
        Number of seconds before socket returns a timeout exception

    Attributes
    ----------
    BYTES_PER_CHANNEL : int
        Number of bytes per sample per channel. EMG and accelerometer data
    CMD_TERM : str
        Command string termination.

    Notes
    -----
    Implementation details can be found in the Delsys SDK reference:
    http://www.delsys.com/integration/sdk/
    """

    BYTES_PER_CHANNEL = 4
    CMD_TERM = '\r\n\r\n'

    def __init__(self, host, cmd_port , timeout, emg_data_port = None, aux_data_port = None, total_emg_channels = 16, total_aux_channels = 144):
        # store all the parameters
        self.host = host
        self.cmd_port = cmd_port
        self.emg_data_port = emg_data_port
        self.aux_data_port = aux_data_port
        self.total_emg_channels = total_emg_channels
        self.total_aux_channels = total_aux_channels
        self.timeout = timeout

        self._min_emg_recv_size = self.total_emg_channels * self.BYTES_PER_CHANNEL
        self._min_aux_recv_size = self.total_aux_channels * self.BYTES_PER_CHANNEL
        self.max_number_of_sensors = 16

        # create the TCP sockets
        self._initialize()

    def _initialize(self):
        # create command socket and consume the servers initial response
        self._comm_socket = socket.create_connection(
            (self.host, self.cmd_port), 10)
        self._comm_socket.recv(1024)


        if self.emg_data_port:
            # create the data socket
            self._emg_data_socket = socket.create_connection(
                (self.host, self.emg_data_port), 10)
            # set data socket to non blocking to not block when there is no data to read, it allows to raise BlockingIOError when all data has been read
            self._emg_data_socket.setblocking(False)

        if self.aux_data_port:
            # create the data socket
            self._aux_data_socket = socket.create_connection(
                (self.host, self.aux_data_port), 10)
            # set data socket to non blocking to not block when there is no data to read, it allows to raise BlockingIOError when all data has been read
            self._aux_data_socket.setblocking(False)


    def start(self):
        """
        Tell the device to begin streaming data.
        """
        self._send_cmd('START')

    def read_all_emg(self):
        """
        Receive all available samples from TCP buffer from the emg port.
        This is a non-blocking method, meaning it could return zero samples when buffer is empty or all samples.

        Returns
        -------
        data : ndarray, shape=(total_channels, number_of_samples)
            Data read from the device. Each channel is a row and each column
            is a point in time.
        """
        packet = bytes()
        lacking_bytes = 0
        while(True):
            try:
                packet += self._emg_data_socket.recv(self._min_emg_recv_size + lacking_bytes)
                relative_packet_length = len(packet) % self._min_emg_recv_size
                if(relative_packet_length != 0):
                    lacking_bytes = self._min_emg_recv_size - relative_packet_length
            except BlockingIOError:
                # if there are no more lacking bytes then break out of the loop (stop accumulating bytes)
                if(lacking_bytes == 0):
                    break
                else:
                    #insecure, because it can loop many many times when connection is very weak, should be timeouted also
                    pass
            except socket.timeout:
                # fill the number of lacking bytes with 0x00
                packet += b'\x00' * (lacking_bytes)
                raise IOError("Device disconnected.")
        number_of_samples = int(len(packet) / self._min_emg_recv_size)
        # unpack what is in the packet as a float32
        data = numpy.asarray(
            struct.unpack('<'+'f'*self.total_emg_channels*number_of_samples, packet), dtype =numpy.float32) #type of data from sdk
        data = numpy.transpose(data.reshape((-1, self.total_emg_channels)))
        return data

    def read_all_aux(self):
        """
        Receive all available samples from TCP buffer from the imu port.
        This is a non-blocking method, meaning it could return zero samples when buffer is empty or all samples.

        Returns
        -------
        data : ndarray, shape=(total_channels, number_of_samples)
            Data read from the device. Each channel is a row and each column
            is a point in time.
        """
        packet = bytes()
        lacking_bytes = 0
        while(True):
            try:
                packet += self._aux_data_socket.recv(self._min_aux_recv_size + lacking_bytes)
                relative_packet_length = len(packet) % self._min_aux_recv_size
                if(relative_packet_length != 0):
                    lacking_bytes = self._min_aux_recv_size - relative_packet_length
            except BlockingIOError:
                # if there are no more lacking bytes then break out of the loop (stop accumulating bytes)
                if(lacking_bytes == 0):
                    break
                else:
                    #insecure, because it can loop many many times when connection is very weak, should be timeouted also
                    pass
            except socket.timeout:
                # fill the number of lacking bytes with 0x00
                packet += b'\x00' * (lacking_bytes)
                raise IOError("Device disconnected.")
        number_of_samples = int(len(packet) / self._min_aux_recv_size)

        # unpack what is in the packet as a float32
        data = numpy.asarray(
            struct.unpack('<'+'f'*self.total_aux_channels*number_of_samples, packet), dtype =numpy.float32) #type of data from sdk
        data = numpy.transpose(data.reshape((-1, self.total_aux_channels)))
        return data

    def stop(self):
        """Tell the device to stop streaming data."""
        self._send_cmd('QUIT')

    def reset(self):
        """Restart the connection to the Trigno Control Utility server."""
        self._initialize()

    def __del__(self):
        try:
            self._comm_socket.close()
        except:
            pass

    @staticmethod
    def _channels_mask(sensors_ids, number_of_channels, channels_per_sensor):
        """
           Create mask for channels to receive data.

           Parameters
           ----------
           sensors_ids : tuple
               Identifiers of used sensors, e.g. (1, 2,) obtains data from sensors 1 and 2.
           number_of_channels : int
               Number of data channels for one measurement (e.g. EMG data is 1 data channel and Quaternion 4 data channels)
           channels_per_sensor : int
               Number of data channels assigned for one sensor

           Returns
           ----------
           sensors_mask : list
               Mask of channels when expected data occurs.

        """
        sensors_mask = []
        for sensor_iter, sensor_id in enumerate(sensors_ids):
            sensor_mask = list(range(channels_per_sensor*sensor_id-channels_per_sensor, channels_per_sensor*sensor_id-channels_per_sensor+number_of_channels))
            sensors_mask.extend(sensor_mask)
        return sensors_mask

    def _send_cmd(self, command, return_reply = False):
        self._comm_socket.send(self._cmd(command))
        raw_resp = self._comm_socket.recv(128)
        formated_resp = self._get_reply(raw_resp)
        if('?') in command:
            print("Query: {} <->  Reply: {}".format(command, formated_resp))
        else:
            print("Command: {} <->  Reply: {}".format(command, formated_resp))
        if return_reply:
            return formated_resp

    def _get_reply(self, response):
        reply = struct.unpack(str(len(response)) + 's', response)
        reply = reply[0].decode(encoding='ascii')
        if(self.CMD_TERM in reply):
            reply = reply.replace(self.CMD_TERM,'')
        return reply

    def set_mode(self,sensor_number, mode_number):
        """
           Command to set the mode the given sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
           mode_number : int
               Desired mode of sensor.
        """
        self._send_cmd(f'SENSOR {sensor_number} SETMODE {mode_number}')

    def set_backwards_compatibility(self, flag = 'ON'):
        """
           Command to set the backwards compatibility. It is on by default.

           Parameters
           ----------
           flag : str
               ON or OFF flag
        """
        self._send_cmd(f'BACKWARDS COMPATIBILITY {flag}')

    def set_upsampling(self, flag = 'ON'):
        """
           Command to set the upsampling. It is on by default.

           Parameters
           ----------
           flag : str
               ON or OFF flag
        """
        self._send_cmd(f'UPSAMPLE {flag}')

    def pair_sensor(self,sensor_number):
        """
           Command to pair sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} PAIR')

    def is_paired(self, sensor_number):
        """
           Query to check if sensor is paired with base.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        reply = self._send_cmd(f'SENSOR {sensor_number} PAIRED?', return_reply=True)
        return reply

    def what_serial(self,sensor_number):
        """
           Query to get unique serial number of sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} SERIAL?', return_reply=False)

    def what_rate(self,sensor_number, channel_number):
        """
           Query to get sampling frequency on the sensor's channel.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
           channel_number : int
               Number of channel
        """
        self._send_cmd(f'SENSOR {sensor_number} CHANNEL {channel_number} RATE?', return_reply=False)

    def where_start(self,sensor_number):
        """
           Query which position in the data buffer a given sensor’s first channel will appear.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} STARTINDEX?', return_reply=False)

    def what_aux_channel_count(self,sensor_number):
        """
           Query the number of AUX channels in use on a given sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} AUXCHANNELCOUNT?', return_reply=False)

    def what_mode(self,sensor_number):
        """
           Query to current mode of a given sensor

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        reply = self._send_cmd(f'SENSOR {sensor_number} MODE?', return_reply = True)
        try:
            print(f'This is {self.CONFIGURATION_MODES[reply]} mode.')
        except:
            print('Unrecognized mode')

    def is_active(self,sensor_number):
        """
           Query the active state of a given sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        reply = self._send_cmd(f'SENSOR {sensor_number} ACTIVE?', return_reply = True)
        return reply

    @staticmethod
    def _cmd(command):
        return bytes("{}{}".format(command, _BaseTrignoDaq.CMD_TERM),
                     encoding='ascii')

    @staticmethod
    def _validate(response):
        s = str(response)
        if 'OK' not in s:
            print("warning: TrignoDaq command failed: {}".format(s))

class TrignoEMG_Aux(_BaseTrignoDaq):
    """
    Delsys Trigno wireless EMG system orientation data.

    Requires the Trigno Control Utility to be running.

    Parameters
    ----------
    channel_range : tuple with 2 ints
        Sensor channels to use, e.g. (lowchan, highchan) obtains data from
        channels lowchan through highchan. Each sensor has three accelerometer
        channels.
    host : str, optional
        IP address the TCU server is running on. By default, the device is
        assumed to be attached to the local machine.
    cmd_port : int, optional
        Port of TCU command messages.
    data_port : int, optional
        Port of TCU accelerometer data access. By default, 50042 is used, but
        it is configurable through the TCU graphical user interface.
    timeout : float, optional
        Number of seconds before socket returns a timeout exception.
    """
    def __init__(self, sensors_mode_number, read_emg, read_acc, read_gyro, read_orientation, sensors_ids, host,
                 cmd_port, emg_port, imu_port, timeout):
        super(TrignoEMG_Aux, self).__init__(
            host=host, cmd_port=cmd_port,timeout=timeout, aux_data_port=imu_port, emg_data_port=emg_port)

        self.read_emg = read_emg
        self.read_acc = read_acc
        self.read_gyro = read_gyro
        self.read_orientation = read_orientation

        # default read imu
        self.emg_data_channels = 1
        if self.read_acc or self.read_gyro:
            self.aux_data_channels = 3
        if self.read_acc and self.read_gyro:
            self.aux_data_channels = 6

        if self.read_orientation:
            self.aux_data_channels = 4
        

        if self.read_emg:
            channels_per_emg_sensor = int(self.total_emg_channels / self.max_number_of_sensors) # 1 for EMG
            self.emg_channels_mask = self._channels_mask(sensors_ids, self.emg_data_channels, channels_per_emg_sensor)

        if self.read_acc or self.read_gyro or self.read_orientation:
            channels_per_aux_sensor = int(self.total_aux_channels / self.max_number_of_sensors) # 9 for quaternion and imu
            self.aux_channels_mask = self._channels_mask(sensors_ids, self.aux_data_channels, channels_per_aux_sensor)


    def read_time_data(self):
        """
        Receive all available samples from TCP buffer with timestamps.
        This is a non-blocking method, meaning it could return zero samples when buffer is empty or all samples.

        Returns
        -------
        data : ndarray, shape=(total_channels, number_of_samples)
            Data read from the device. Each channel is a row and each column
            is a point in time.
        """

        if self.read_emg:
            emg_data = super(TrignoEMG_Aux,self).read_all_emg()
            #emg_data = emg_data[self.emg_channels_mask,:]


        if self.read_acc or self.read_gyro or self.read_orientation:
            aux_data = super(TrignoEMG_Aux,self).read_all_aux()
            #aux_data = aux_data[self.aux_channels_mask,:]


        return emg_data, aux_data
    
class Sensor():
    """


    """
    def __init__(self, operation_mode, sensors_mode_number, read_emg, read_acc, read_gyro, read_orientation, sensors_ids, sensors_labels, host, cmd_port, emg_port, imu_port, timeout):
        self.operation_mode = operation_mode
        self.sensors_mode_number = sensors_mode_number
        self.sensors_ids = sensors_ids
        self.sensors_labels = sensors_labels
        self.host = host
        self.cmd_port = cmd_port
        self.emg_port = emg_port
        self.imu_port = imu_port
        self.read_emg = read_emg
        self.read_acc = read_acc
        self.read_gyro = read_gyro
        self.read_orientation = read_orientation
        self.timeout = timeout

        self.active_sensors = defaultdict(list)
        self.add_sensors()

    def add_sensors(self):
        """
        Add sensor to sensor bundle.

        Parameters
        ----------
        sensors_mode : str
            Desired mode of sensors. (e.g. 'ORIENTATION' or 'EMG')
        sensors_ids : tuple
            Identifiers of used sensors, e.g. (1, 2,) obtains data from
            sensors 1 and 2.
        sensors_labels : tuple
            Labels for used sensors, e.g ('ORIENTATION1', 'ORIENTATION2',). When nothing
            passed then identifiers are used as labels.
        host : str
            IP address of Delsys Trigno Controll Utility or localhost
        """
        if(len(self.sensors_labels) != len(self.sensors_ids)):
            print(len(self.sensors_labels))
            print(len(self.sensors_ids))
            self.sensors_labels = self.sensors_ids
            print(f'Incorrent number of sensor labels. Using sensor ids: {self.sensors_labels} as labels')

        trigno_sensors = self.__create_sensors(self.sensors_mode_number, self.read_emg, self.read_acc, self.read_gyro, self.read_orientation, self.sensors_ids, self.host,
                 self.cmd_port, self.emg_port, self.imu_port, self.timeout)

        if(trigno_sensors):
            if(type(trigno_sensors) in [type(sensor) for sensor in self.active_sensors[self.sensors_labels]]):
                print(f'There is an existing sensor with mode: {self.sensors_mode_number} and label: {self.sensors_labels}. Try to change the sensor label or configuration of existing sensor.')
            else:
                self.active_sensors[self.sensors_labels].append(trigno_sensors)
                print(f'Sensors {self.sensors_ids} with mode: {self.sensors_mode_number} and label: {self.sensors_labels} has been added.')
        else:
            print('There are unpaired sensors. Please configure sensors adding.')


    def __create_sensors(self, sensors_mode_number, read_emg, read_acc, read_gyro, read_orientation, sensors_ids, host,
                 cmd_port, emg_port, imu_port, timeout):
        try:
            trigno_sensor = TrignoEMG_Aux(sensors_mode_number, read_emg, read_acc, read_gyro, read_orientation, sensors_ids, host,
                 cmd_port, emg_port, imu_port, timeout)
            for sensor_id in self.sensors_ids:
                reply_paired = trigno_sensor.is_paired(sensor_id)
                if (reply_paired == 'NO'):
                    print(f'Sensor {sensor_id} is unpaired. Please pair it now...')
                    trigno_sensor.pair_sensor(sensor_id)
                    response = input("press any key to proceed or press q to quit.")
                    if response == 'q':
                        return None
                    else:
                        self.__create_sensors()
                else:
                    reply_active = trigno_sensor.is_active(sensor_id)
                    if (reply_active == 'YES'):
                        print(f'Sensor {sensor_id} is active.')
                    else:
                        print(f'Sensor {sensor_id} is inactive.')
                trigno_sensor.set_mode(sensor_id, self.sensors_mode_number)
            return trigno_sensor
        except:
            print(f'Connection problem or unrecognized sensor mode {self.sensors_mode_number}.')
            return None


    def start_acquisition(self):
        """
        Start data acquisition from all sensors.
        """
        try:
            list(self.active_sensors.values())[0][0].start()
        except:
            print('Could not start acquisition. There has been no sensors added.')

    def stop_acquisition(self):
        """
        Stop data acquisition from all sensors.
        """
        try:
            list(self.active_sensors.values())[0][0].stop()
        except:
            print('Could not stop acquisition. There has been no sensors added.')

    def get_sensor_data(self):
        try:
            if not(self.sensors_labels):
                self.sensors_labels = (*(*self.active_sensors,),)
            elif not(set(self.active_sensors.keys()).intersection(set((self.sensors_labels,)))):
                raise ValueError("Unrecognized sensors labels.")
            #for sensors_label in self.sensors_labels:
            for sensors in self.active_sensors[self.sensors_labels]:
                emg_data, aux_data = sensors.read_time_data()
                return emg_data, aux_data 
        except Exception:
            print("sensordata not working")













