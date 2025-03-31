#include <WiFi.h>
#include <Adafruit_NeoPixel.h>
#include <time.h>

// WLAN-Daten
const char* ssid = "Mine";
const char* password = "31413141";

// NTP-Server
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 3600;
const int daylightOffset_sec = 0; // Remove daylight offset; NTP should handle DST

// Zeitvariablen
struct tm timeinfo;
unsigned long startMillis;
unsigned long long latestTimestamp = 0;

// Pin-Definitionen
#define FSR0_0 1
#define FSR0_1 2
#define FSR0_2 3
#define FSR0_3 4
#define FSR1_0 5
#define FSR1_1 6
#define FSR1_2 7
#define FSR1_3 10
#define FSR2_0 12
#define FSR2_1 13
#define FSR2_2 14
#define FSR2_3 15
#define MIX 17
#define E 42
#define S3 41
#define S2 40
#define S1 39
#define S0 38

// Sensor-Konfiguration
#define NUM_SEN         6
#define VAL_PER_SEN     4
#define NUM_DATA        (NUM_SEN * VAL_PER_SEN)
#define NUM_DIREKT_READ 12
#define NUM_MIX         (NUM_DATA - NUM_DIREKT_READ)

uint8_t sensor_pins[NUM_DIREKT_READ] = {FSR0_0, FSR0_1, FSR0_2, FSR0_3, FSR1_0, FSR1_1, FSR1_2, FSR1_3, FSR2_0, FSR2_1, FSR2_2, FSR2_3};
// Array für die Sensorwerte als float statt double
float fmg_data[NUM_DATA] = {0};  // Array mit float statt double
uint8_t startDelimiter = 0xFF;  // Start-Trennzeichen
uint8_t endDelimiter = 0x00;    // End-Trennzeichen


// LED-Konfiguration
#define PIN        18
#define NUMPIXELS  1
#define BRIGHTNESS 50
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
    Serial.begin(115200);
    
    setup_pin();
    setup_led(); 
    setup_wifi();

    // NTP initialisieren
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    while (!getLocalTime(&timeinfo)) {} // Warte auf gültige Zeit
    startMillis = millis();
}

void setup_pin() {
    for (uint8_t i = 0; i < NUM_DIREKT_READ; i++) {
        pinMode(sensor_pins[i], INPUT);
    }
    pinMode(MIX, INPUT);
    pinMode(E, OUTPUT);
    digitalWrite(E, HIGH);
    pinMode(S0, OUTPUT);
    pinMode(S1, OUTPUT);
    pinMode(S2, OUTPUT);
    pinMode(S3, OUTPUT);
}

void setup_led() {
    pixels.begin();
    pixels.setBrightness(BRIGHTNESS);
    pixels.show();
}

void setup_wifi() {
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        setup_wifi();
    }

    FSRReading();
    getLocalTime(&timeinfo);
    updateTimestamp(timeinfo);
    sendFmgDataSerial();

    delay(10);
}

void FSRReading() {
    for (uint8_t sen = 0; sen < NUM_SEN; sen++) {
        for (uint8_t val = 0; val < VAL_PER_SEN; val++) {
            uint8_t Idx = sen * VAL_PER_SEN + val;
            if (Idx < NUM_DIREKT_READ) {
                fmg_data[Idx] = analogRead(sensor_pins[Idx]) * 0.08225 * (5.0 / 1023.0);
            } else {
                uint8_t mixChannel = Idx - NUM_DIREKT_READ;
                if (mixChannel > 7) mixChannel += 4;
                SetMixCh(mixChannel);
                fmg_data[Idx] = analogRead(MIX) * 0.08225 * (5.0 / 1023.0);
                digitalWrite(E, HIGH);
            }
        }
    }
}

void SetMixCh(byte Ch) {
    digitalWrite(E, LOW);
    digitalWrite(S0, bitRead(Ch, 0));
    digitalWrite(S1, bitRead(Ch, 1));
    digitalWrite(S2, bitRead(Ch, 2));
    digitalWrite(S3, bitRead(Ch, 3));
}

void sendFmgDataSerial() {


    // Sende das Start-Trennzeichen
    Serial.write(startDelimiter);

    // Sende den Zeitstempel als Long Integer (8 Bytes)
    Serial.write((uint8_t*)&latestTimestamp, sizeof(latestTimestamp));

    // Sende die Floats der Sensoren (24 Sensorwerte, je 4 Bytes für float)
    for (int i = 0; i < NUM_DATA; i++) {
        Serial.write((uint8_t*)&fmg_data[i], sizeof(fmg_data[i]));  // Sende die 4 Bytes für jedes `float`
    }

    // Sende das End-Trennzeichen
    Serial.write(endDelimiter);
}


void updateTimestamp(struct tm &timeinfo) {
    latestTimestamp = (unsigned long long)(timeinfo.tm_hour) * 10000000 +
                      (unsigned long long)(timeinfo.tm_min) * 100000 +
                      (unsigned long long)(timeinfo.tm_sec) * 1000 +
                      (unsigned long long)((millis() - startMillis) % 1000);
}
