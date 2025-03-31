import struct
import time
import serial
import queue
import threading
import os
import csv
from datetime import datetime  
# Serielle Verbindung konfigurieren

fmg_error_event = threading.Event()
stop_fmg=0
serial_port = 'COM13'  # Passe dies an deinen Port an (z. B. 'COM3' unter Windows)
baud_rate = 115200  # Baudrate, passend zum Arduino
default_value=3.292814016342163
# Initialisiere die Queue für die empfangenen Nachrichten


message_queue = queue.Queue(maxsize=10000)
is_recording = False
stop_event = threading.Event()
batch_size = 100
file_lock = threading.Lock()
csvfile = None
########
debug_mode=0 # liveprints all fmg sensors that change from 3.29 V (O)


def read_serial():
    global is_recording, stop_fmg
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Verbindung zu {serial_port} hergestellt.")

        last_received_time = time.time()  # Zeitpunkt des letzten gültigen Datenempfangs

        while not stop_fmg:
            if ser.in_waiting > 0:
                start_delim = ser.read(1)
                if start_delim == b'\xFF':  
                    timestamp_bytes = ser.read(8)
                    timestamp = struct.unpack('Q', timestamp_bytes)[0]
                    timestamp_win = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Timestamp with millisecond precision

                    sensor_data = []
                    for i in range(24):
                        sensor_bytes = ser.read(4)
                        sensor_value = struct.unpack('f', sensor_bytes)[0]
                        if debug_mode and sensor_value != default_value:
                            print(f"Sensor{i} is {sensor_value}")
                        sensor_data.append(sensor_value)

                    end_delim = ser.read(1)
                    if end_delim == b'\x00':
                        data_with_timestamp = sensor_data + [timestamp] + [timestamp_win]

                        if is_recording:
                            message_queue.put_nowait(data_with_timestamp)
                            fmg_error_event.clear()  # Fehlerstatus zurücksetzen
                        
                        last_received_time = time.time()  # Zeit aktualisieren
                      
            else:
                # Prüfe, ob seit 4 Sekunden keine Daten empfangen wurden
                if time.time() - last_received_time > 4:
                    fmg_error_event.set()
                    print("4 seconds")
                    last_received_time = time.time()

    except serial.SerialException as e:
        print(f"Fehler bei der seriellen Verbindung: {e}")
        fmg_error_event.set()




def start_recording(participant_num, test_order):
    """
    Startet die Aufzeichnung der Sensordaten in eine CSV-Datei.
    """
    global is_recording, csvfile
    is_recording = True
    stop_event.clear()
    
    output_dir = f'../data/input_data/{test_order}/'
    os.makedirs(output_dir, exist_ok=True)
    csv_file_path = os.path.join(output_dir, f'fmg_data_P{participant_num}.csv')
    
    csvfile = open(csv_file_path, 'a', newline='')
    csvwriter = csv.writer(csvfile)
    
    if os.stat(csv_file_path).st_size == 0:
        header = ['FSR{:02d}'.format(i) for i in range(1, 25)] + ['Timestamp']+['Timestamp_win']
        csvwriter.writerow(header)
    
    threading.Thread(target=file_writer_thread, daemon=True).start()
    print(f"Aufzeichnung gestartet für Teilnehmer {participant_num}, Test {test_order}.")

def file_writer_thread():
    """
    Schreibt Daten aus der Queue in die CSV-Datei.
    """
    global csvfile
    buffer = []
    while is_recording or not message_queue.empty():
        try:
            item = message_queue.get(timeout=1)
            buffer.append(item)
            if len(buffer) >= batch_size:
                write_to_csv(buffer)
                buffer.clear()
            message_queue.task_done()
        except queue.Empty:
            continue
    if buffer:
        write_to_csv(buffer)
        buffer.clear()
    stop_event.set()

def write_to_csv(buffer):
    """
    Schreibt die gepufferten Daten in die CSV-Datei.
    """
    global csvfile
    with file_lock:
        if csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerows(buffer)
        else:
            print("CSV-Datei nicht geöffnet.")

def stop_recording():
    """
    Stoppt die Aufzeichnung und speichert verbleibende Daten.
    """
    global is_recording,stop_fmg
    stop_fmg=1
    is_recording = False
    message_queue.join()
    stop_event.wait()
    with file_lock:
        if csvfile:
            csvfile.close()
            print("Datei geschlossen, Daten gespeichert.")
