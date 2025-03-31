from PIL import Image, ImageDraw, ImageFont
import os

def tausche_labels_im_bild(image_path, label1, label2, output_path):
    # Bild laden
    img = Image.open(image_path)
    
    # Zeichenwerkzeug erstellen
    draw = ImageDraw.Draw(img)
    
    # Schriftart festlegen (achte darauf, dass die Schriftart existiert oder setze eine Standard-Schriftart)
    try:
        font = ImageFont.truetype("arial.ttf", 200)
    except IOError:
        font = ImageFont.load_default()
    
    # Angenommene Positionen der Labels (müsstest du ggf. anpassen)
    griff_position = (4350, 400)  # Beispielkoordinaten für "Griff"
    objekt_position = (2500, 400)  # Beispielkoordinaten für "Objekt"
    
    # Farbe für "lightgreen" (für den Hintergrund)
    heading_banner_color = "lightgreen"  # Helles Grün für den Hintergrund

    # Berechne die Größe des Textes mit textbbox
    # textbbox gibt eine Bounding Box des Textes zurück (x1, y1, x2, y2)
    bbox1 = draw.textbbox((0, 0), label1, font=font)
    bbox2 = draw.textbbox((0, 0), label2, font=font)

    # Breite und Höhe des Textes extrahieren
    text_width_1 = bbox1[2] - bbox1[0]  # Breite von label1
    text_height_1 = bbox1[3] - bbox1[1]  # Höhe von label1
    text_width_2 = bbox2[2] - bbox2[0]  # Breite von label2
    text_height_2 = bbox2[3] - bbox2[1]  # Höhe von label2
    
    # Padding für die "delete box" (grüne Box um den Text)
    padding = 60  # Hier wird der Bereich um den Text größer gemacht
    padding2 = 11  # Hier wird der Bereich um den Text größer gemacht
    # Anpassung der Griff Position (hier verschieben wir die y-Koordinate)
    griff_position_y_adjusted = griff_position[1] - 20  # Beispielwert, um die Box höher zu setzen

    # Grüne Boxen um die Textpositionen zeichnen (größerer Bereich)
    draw.rectangle([griff_position[0] - padding, griff_position_y_adjusted - padding, 
                    griff_position[0] + text_width_1 + padding, griff_position_y_adjusted + text_height_1 + padding], 
                   fill=heading_banner_color)
    
    draw.rectangle([objekt_position[0] - padding2, objekt_position[1] - padding2, 
                    objekt_position[0] + text_width_2 + padding2, objekt_position[1] + text_height_2 + padding2], 
                   fill=heading_banner_color)
    
    # Jetzt die neuen Labels zeichnen
    draw.text(griff_position, label2, fill="black", font=font)  # "Objekt" an die Position von "Griff" setzen
    draw.text(objekt_position, label1, fill="black", font=font)  # "Griff" an die Position von "Objekt" setzen

    # Bild speichern
    img.save(output_path)

# Beispielaufruf der Funktion für Bild 1
for current_action_num in range(1, 75):  # von 1 bis 74, z.B. nur für action_1
    input_image_path = f'../images/Final_images/action_{current_action_num}.jpg'
    output_image_path = f'../images/Slides/action_{current_action_num}.jpg'
    
    # Stelle sicher, dass die Datei existiert, bevor du versuchst, sie zu bearbeiten
    if os.path.exists(input_image_path):
        tausche_labels_im_bild(input_image_path, "Griff", "Objekt", output_image_path)
        print(f'Bild action_{current_action_num} wurde bearbeitet und gespeichert.')
    else:
        print(f'Bild action_{current_action_num} nicht gefunden.')
