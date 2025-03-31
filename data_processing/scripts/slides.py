from PIL import Image, ImageDraw, ImageFont

# Aktuelle Aktionsnummer
current_action_num = 59
textl = ''
textr = ''
title_text = "Binde die Schnürsenkel und löse sie wieder"
title_eng = "Tie the laces of the shoe and untie them "

# Bilder laden
img1 = Image.open(f'../images/Old_images/action_{current_action_num}_leer.jpg')
img2 = Image.open(f'../images/Old_images/action_{current_action_num}.jpg')

current_action_num = 58


# Bilder um 90 Grad drehen
img1 = img1.rotate(270, expand=True)
img2 = img2.rotate(270, expand=True)

# Platz für Überschriften berechnen
banner_height = 600  # Gesamthöhe der Banner
title_banner_height = 400  # Höhe des blauen Titelbanners
heading_banner_height = banner_height - title_banner_height  # Höhe des grünen Überschriftenbanners

number_box_width = max(img1.width, img2.width)  # Platz für Zahlenfelder

# Collage-Größe berechnen
collage_width = img1.width + img2.width + number_box_width * 2
collage_height = max(img1.height, img2.height) + banner_height

# Neue Collage erstellen
collage = Image.new("RGB", (collage_width, collage_height), "white")

# Farben definieren
title_banner_color = "lightblue"  # Farbe für den Titelbereich
heading_banner_color = "lightgreen"  # Farbe für den Überschriftenbereich
text_color = "black"
title_color = "black"  # Titel in einer anderen Farbe
title_color_eng = "darkblue"  # Titel in einer anderen Farbe
# Banner zeichnen
draw = ImageDraw.Draw(collage)

# Titel-Banner zeichnen
draw.rectangle([0, 0, collage_width, title_banner_height], fill=title_banner_color)

# Überschriften-Banner zeichnen
heading_banner_start = title_banner_height
draw.rectangle([0, heading_banner_start, collage_width, banner_height], fill=heading_banner_color)

# Schriftart für Bannertext, Titel und Zahlen festlegen
try:
    title_font = ImageFont.truetype("arial.ttf", 230)  # Schriftgröße für den Titel
    english_font = ImageFont.truetype("arial.ttf", 120)  # Schriftgröße für den englischen Titel
    banner_font = ImageFont.truetype("arial.ttf", 200)  # Schriftgröße für Bannertext
    number_font = ImageFont.truetype("arial.ttf", 400)  # Schriftgröße für Zahlen
except IOError:
    title_font = ImageFont.load_default()
    english_font = ImageFont.load_default()
    banner_font = ImageFont.load_default()
    number_font = ImageFont.load_default()

# Platz für Titel bestimmen
title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
title_width, title_height = title_bbox[2] - title_bbox[0], title_bbox[3] - title_bbox[1]

# Titel mittig im Titelbereich platzieren
title_x = (collage_width - title_width) / 2
title_y = (title_banner_height - title_height) / 4 -50 # Titel weiter oben platzieren

# Titel zeichnen
draw.text((title_x, title_y), title_text, fill=title_color, font=title_font)

# Englische Version des Titels hinzufügen
english_bbox = draw.textbbox((0, 0), title_eng, font=english_font)
english_width, english_height = english_bbox[2] - english_bbox[0], english_bbox[3] - english_bbox[1]

# Englischen Titel mittig unter dem Haupttitel platzieren
english_x = (collage_width - english_width) / 2
english_y = title_y + title_height + 80  # Abstand von 20 Pixeln unterhalb des Haupttitels

draw.text((english_x, english_y), title_eng, fill=title_color_eng, font=english_font)

# Überschriften erstellen
headings = ["Start", "Griff", "Objekt", "Ziel"]
section_width = collage_width // len(headings)

# Überschriften zentrieren und im unteren Teil des Banners platzieren
gap_between_title_and_text = 20  # Abstand zwischen Titel und Text
for i, heading in enumerate(headings):
    x_start = i * section_width
    x_end = (i + 1) * section_width

    # Textbreite und Höhe berechnen
    text_bbox = draw.textbbox((0, 0), heading, font=banner_font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]

    # Textposition berechnen
    text_x = x_start + (section_width - text_width) / 2
    text_y = heading_banner_start + (heading_banner_height - text_height) / 2 + gap_between_title_and_text-40  # Text mittig im grünen Banner

    # Text auf das Banner zeichnen
    draw.text((text_x, text_y), heading, fill=text_color, font=banner_font)

# Platz für Zahlenfelder
number_field_left = Image.new("RGB", (number_box_width, collage_height - banner_height), "white")
number_field_right = Image.new("RGB", (number_box_width, collage_height - banner_height), "white")

# Zahlen in Felder zeichnen
draw_left = ImageDraw.Draw(number_field_left)
draw_right = ImageDraw.Draw(number_field_right)

# Text mittig in Zahlenfelder platzieren
text_bbox = draw_left.textbbox((0, 0), textl, font=number_font)
text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
draw_left.text(((number_box_width - text_width) / 2, (collage_height - banner_height - text_height) / 2), textl, fill="black", font=number_font)

text_bbox = draw_right.textbbox((0, 0), textr, font=number_font)
text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
draw_right.text(((number_box_width - text_width) / 2, (collage_height - banner_height - text_height) / 2), textr, fill="black", font=number_font)

# Bilder und Felder in die Collage einfügen
collage.paste(number_field_left, (0, banner_height))  # Linkes Zahlenfeld
collage.paste(img1, (number_box_width, banner_height))  # Erstes Bild
collage.paste(img2, (number_box_width + img1.width, banner_height))  # Zweites Bild
collage.paste(number_field_right, (number_box_width + img1.width + img2.width, banner_height))  # Rechtes Zahlenfeld

# Collage speichern
collage.save(f'../images/Final_images/action_{current_action_num}.jpg')
