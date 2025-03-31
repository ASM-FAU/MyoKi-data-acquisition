import pandas as pd
from datetime import datetime, timedelta

import pandas as pd
from datetime import datetime, timedelta

def  aux_data_processing(input_file_path, output_file_path):
    # Schritt 1: CSV-Datei laden
    data = pd.read_csv(input_file_path)

    # Schritt 2: Zeitstempel in datetime-Objekte konvertieren
    data['Timestamp'] = pd.to_datetime(data['Timestamp'], format='%Y-%m-%d %H:%M:%S.%f')

    # Schritt 3: Cluster identifizieren
    clusters = []
    current_cluster = [0]  # Startet mit dem Index des ersten Eintrags

    for i in range(1, len(data)):
        if data['Timestamp'][i] == data['Timestamp'][i - 1]:
            current_cluster.append(i)
        else:
            clusters.append(current_cluster)
            current_cluster = [i]
    clusters.append(current_cluster)  # Letztes Cluster hinzufügen

    # Schritt 4: Rückwärts durch die Cluster iterieren und interpolieren
    for i in range(len(clusters) - 1, 0, -1):
        current_cluster = clusters[i]
        previous_cluster = clusters[i - 1]

        # Letzter Wert des aktuellen und vorherigen Clusters
        end_time = data['Timestamp'][current_cluster[-1]]
        start_time = data['Timestamp'][previous_cluster[-1]]

        # Gesamtzeitintervall zwischen den letzten Werten der Cluster
        total_interval = (end_time - start_time).total_seconds()

        # Anzahl der zu interpolierenden Werte im aktuellen Cluster (ohne den letzten Wert)
        num_values_to_interpolate = len(current_cluster) - 1

        if num_values_to_interpolate > 0:
            # Zeitintervall für die Interpolation
            interval = total_interval / (num_values_to_interpolate + 1)

            # Interpolierte Zeitstempel berechnen
            for j in range(num_values_to_interpolate):
                interpolated_time = start_time + timedelta(seconds=interval * (j + 1))
                data.at[current_cluster[j], 'Timestamp'] = interpolated_time

    # Schritt 5: Zeitstempel zurück in das gewünschte Format konvertieren
    data['Timestamp'] = data['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')

    # Schritt 6: Modifizierte Daten in eine neue CSV-Datei speichern
    data.to_csv(output_file_path, index=False)

    print(f"Die Zeitstempel wurden interpoliert und die Datei wurde gespeichert: {output_file_path}")



