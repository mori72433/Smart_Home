#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_AHTX0.h>
#include <ScioSense_ENS160.h>
#include <ArduinoJson.h>

// ===== PIN CONFIGURATION =====
#define SDA_PIN 21
#define SCL_PIN 22

// ===== DISPLAY CONFIGURATION =====
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_ADDR 0x3C

// ===== NETWORK CONFIGURATION =====
const char* ssid = "Thulshan";
const char* password = "20020407";
const char* apiUrl = "https://57.128.230.197/api/sensor-data";  // HTTPS on port 443

// TLS root CA certificate used by the HTTPS server.
// Replace with your server CA certificate (PEM format).
const char* rootCa =
"-----BEGIN CERTIFICATE-----\n"
"MIIDJDCCAgygAwIBAgIUTX15jzXESz6t8z8ZWwE96O6zey0wDQYJKoZIhvcNAQEL\n"
"BQAwGTEXMBUGA1UEAwwONTcuMTI4LjIzMC4xOTcwHhcNMjYwNTAzMDQ0MTMyWhcN\n"
"MjcwNTAzMDQ0MTMyWjAZMRcwFQYDVQQDDA41Ny4xMjguMjMwLjE5NzCCASIwDQYJ\n"
"KoZIhvcNAQEBBQADggEPADCCAQoCggEBAK/qP1q0BZvw2CPhPOup+SOqujGohpcv\n"
"PUBbSO3F0LVPklBoZbzRdAelDLLBn3/PQCcWNWudZu2joT/LnEd17PrPy63xN5qa\n"
"fyPuSsAuVe53/bh3fURGkwLXqJlKHbjlWJ8Kjs0bFto+7XVJxqiZHN3VySfZh68n\n"
"r5Wi/pI7KOGkvs55MiUzdAk9f/fSaBGL7iH0aSL846RFdkcjN9K20xmXW1itoewR\n"
"OYvfldJJZvhgqqfbFctfy+NplHpHTOVK8AotJEzr9JE7n6GAeMJ+N4VQWdvn6bat\n"
"oM2gRlVzW4eu2V2qaHdl62r4/RBbDf1ziruYzU/uP73WxQol9CBwYa8CAwEAAaNk\n"
"MGIwHQYDVR0OBBYEFEmm1gKzdFyGgCE3VZPGAYzKTcP0MB8GA1UdIwQYMBaAFEmm\n"
"1gKzdFyGgCE3VZPGAYzKTcP0MA8GA1UdEwEB/wQFMAMBAf8wDwYDVR0RBAgwBocE\n"
"OYDmxTANBgkqhkiG9w0BAQsFAAOCAQEAAUj18Nj71b3IAw0a7V8acfkU5a7BHnGh\n"
"EDMAOuI5Y2Bm9TWd4wwUVDxgudpGOEAEekEYcjd3NVEahkKZN3PxaF8iskNcZHjJ\n"
"r6Syc8A9Bz+97dLpahchCjQEiRN2EAh+7Usz768vj6E7Jrz6HW3+6/krm6H50DDQ\n"
"bCFeEJeMQnAC8RcKy4GzPapnxaQ8i0Zph+nmBf9W0qAi5sXF7J3RETl8ekVj+G1v\n"
"0Ccz1CJ9iZxfMCiv4IqKGVne71siseYRVC2FAOoaklNtWxpKAasvnPg8jwUGOhiF\n"
"sg019Q3Zd1eBAXb8l07vmEtBXYLau/cnFYGEdHOyqe+/IHRhi+8KCg==\n"
"-----END CERTIFICATE-----\n";

// ===== SENSOR CONFIGURATION =====
#define SEND_INTERVAL_MS 5000  // Send data every 5 seconds
#define RECONNECT_INTERVAL_MS 30000  // Try WiFi reconnect every 30 seconds

// ===== GLOBAL VARIABLES =====
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
Adafruit_AHTX0 aht;
ScioSense_ENS160 ens160(0x53);

unsigned long lastSendTime = 0;
unsigned long lastReconnectTime = 0;
uint32_t sensorCount = 0;
bool sensorsReady = false;
bool wifiReady = false;

// Forward declaration for helper used before its definition
void displayMessage(const char* line1, const char* line2 = "", const char* line3 = "");

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n\n===== ESP32 Smart Home Sensor System =====");
  Serial.println("Initializing...\n");

  // ===== DISPLAY INITIALIZATION =====
  Wire.begin(SDA_PIN, SCL_PIN);
  
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[ERROR] OLED display not found at address 0x3C!");
    while (1) delay(100);
  }
  Serial.println("[OK] OLED display initialized");

  displayMessage("Smart Home", "Initializing...");

  // ===== AHT SENSOR INITIALIZATION =====
  if (!aht.begin()) {
    Serial.println("[ERROR] AHT sensor not found!");
    displayMessage("ERROR", "AHT Sensor", "Not Found");
    while (1) delay(100);
  }
  Serial.println("[OK] AHT temperature/humidity sensor initialized");
  delay(500);

  // ===== ENS160 SENSOR INITIALIZATION =====
  if (!ens160.begin()) {
    Serial.println("[ERROR] ENS160 sensor not found!");
    displayMessage("ERROR", "ENS160", "Not Found");
    while (1) delay(100);
  }
  Serial.println("[OK] ENS160 air quality sensor initialized");
  
  delay(1000);
  
  if (!ens160.available()) {
    Serial.println("[ERROR] ENS160 sensor not available!");
    displayMessage("ERROR", "ENS160", "Not Available");
    while (1) delay(100);
  }

  ens160.setMode(ENS160_OPMODE_STD);
  Serial.println("[OK] ENS160 operating mode set to Standard");
  
  sensorsReady = true;
  delay(1000);

  // ===== WiFi INITIALIZATION =====
  connectToWiFi();
  
  Serial.println("\n===== System Ready =====\n");
  displayMessage("System Ready", "Starting...");
  delay(2000);

}

void loop() {
  unsigned long now = millis();
  
  // ===== WiFi RECONNECTION CHECK =====
  if (!wifiReady && (now - lastReconnectTime) >= RECONNECT_INTERVAL_MS) {
    connectToWiFi();
    lastReconnectTime = now;
  }

  // ===== SENSOR DATA READING & TRANSMISSION =====
  if ((now - lastSendTime) >= SEND_INTERVAL_MS) {
    readAndSendSensorData();
    lastSendTime = now;
    sensorCount++;
  }

  delay(100);
}

// ===== HELPER FUNCTIONS =====

void connectToWiFi() {
  Serial.println("\n[WiFi] Attempting connection...");
  displayMessage("WiFi", "Connecting...");
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attemptCount = 0;
  const int maxAttempts = 20;
  
  while (WiFi.status() != WL_CONNECTED && attemptCount < maxAttempts) {
    delay(500);
    Serial.print(".");
    attemptCount++;
  }
  
  Serial.println();
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WiFi] Connected! IP: ");
    Serial.println(WiFi.localIP());
    displayMessage("WiFi", "Connected", WiFi.localIP().toString().c_str());
    wifiReady = true;
    delay(1500);
  } else {
    Serial.println("[WiFi] Connection failed. Will retry later.");
    displayMessage("WiFi", "Failed", "Retry in 30s");
    wifiReady = false;
  }
}

void displayMessage(const char* line1, const char* line2, const char* line3) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(line1);
  display.println(line2);
  if (strlen(line3) > 0) {
    display.println(line3);
  }
  display.display();
}

void readAndSendSensorData() {
  if (!sensorsReady) {
    Serial.println("[Sensor] Sensors not ready!");
    return;
  }

  // ===== READ TEMPERATURE & HUMIDITY =====
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  float temperature = temp.temperature;
  float hum = humidity.relative_humidity;

  // ===== READ AIR QUALITY =====
  if (ens160.available()) {
    ens160.measure(true);
  }
  int aqi = ens160.getAQI();
  int tvoc = ens160.getTVOC();
  int eco2 = ens160.geteCO2();

  // ===== LOG SENSOR DATA =====
  Serial.println("\n===== SENSOR READING #" + String(sensorCount) + " =====");
  Serial.print("[Temp] ");  Serial.print(temperature, 1); Serial.println(" °C");
  Serial.print("[Hum]  ");  Serial.print(hum, 1); Serial.println(" %");
  Serial.print("[CO2] ");   Serial.print(eco2); Serial.println(" ppm");
  Serial.print("[TVOC] ");  Serial.print(tvoc); Serial.println(" ppb");
  Serial.print("[AQI]  ");  Serial.println(aqi);

  // ===== UPDATE DISPLAY =====
  displaySensorData(temperature, hum, eco2, tvoc, aqi);

  // ===== SEND TO API =====
  if (wifiReady) {
    sendToAPI(temperature, hum, eco2, tvoc, aqi);
  } else {
    Serial.println("[API] WiFi not connected - buffering data");
  }
}

void displaySensorData(float temp, float humidity, int co2, int tvoc, int aqi) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);

  display.print("T: "); display.print(temp, 1); display.println("C");
  display.print("H: "); display.print(humidity, 1); display.println("%");
  display.print("CO2: "); display.print(co2); display.println("ppm");
  display.print("TVOC: "); display.print(tvoc); display.println("ppb");
  display.print("AQI: "); display.println(aqi);
  
  if (wifiReady) {
    display.setCursor(0, 56);
    display.setTextSize(1);
    display.println("WiFi: OK");
  }

  display.display();
}

void sendToAPI(float temperature, float humidity, int co2, int tvoc, int aqi) {
  WiFiClientSecure client;
  HTTPClient http;

  client.setCACert(rootCa);
  
  // ===== BUILD JSON PAYLOAD =====
  StaticJsonDocument<256> doc;
  doc["temperature"] = round(temperature * 10) / 10.0;
  doc["humidity"] = round(humidity * 10) / 10.0;
  doc["co2"] = co2;
  doc["tvoc"] = tvoc;
  doc["aqi"] = aqi;
  
  String payload;
  serializeJson(doc, payload);

  Serial.println("[API] Sending: " + payload);
  Serial.println("[API] URL: " + String(apiUrl));

  // ===== SEND HTTP POST REQUEST =====
  if (!http.begin(client, apiUrl)) {
    Serial.println("[API] HTTPS begin failed. Check API URL and TLS certificate.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.setConnectTimeout(5000);
  http.setTimeout(5000);
  
  int httpResponseCode = http.POST(payload);

  if (httpResponseCode == 200 || httpResponseCode == 201) {
    String response = http.getString();
    Serial.print("[API] Success (200): ");
    Serial.println(response);
    Serial.println("[API] Data transmitted successfully\n");
  } else if (httpResponseCode > 0) {
    Serial.print("[API] Response Code: ");
    Serial.println(httpResponseCode);
    String response = http.getString();
    Serial.println("[API] Response: " + response);
  } else {
    Serial.print("[API] Error: ");
    Serial.println(http.errorToString(httpResponseCode));
  }

  http.end();
}