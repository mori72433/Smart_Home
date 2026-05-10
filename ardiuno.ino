#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_AHTX0.h>
#include <ScioSense_ENS160.h>

// ===== I2C / OLED =====
#define SDA_PIN 21
#define SCL_PIN 22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_ADDR 0x3C
#define MOTION_PIN 27

// ===== WIFI =====
const char* ssid = "VIRANGA";
const char* password = "20020407";

// ===== API =====
// Use your real domain or server IP here
const char* apiUrl = "https://vsh.akaigen.online/api/sensor-data-xor";

// ===== XOR KEY (from your config) =====
const char* XOR_KEY_HEX = "A1B2C3D4";

// ===== SEND INTERVAL =====
const unsigned long SEND_INTERVAL_MS = 20000;
const unsigned long MOTION_HOLD_MS = 3600000;

// ===== OBJECTS =====
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
Adafruit_AHTX0 aht;
ScioSense_ENS160 ens160(0x53);

// ===== GLOBALS =====
unsigned long lastSendTime = 0;
bool ahtReady = false;
bool ensReady = false;
unsigned long motionActiveUntil = 0;

uint8_t xorKey[32];
size_t xorKeyLen = 0;

// ---------- HEX HELPERS ----------
int hexValue(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

bool loadXorKey(const char* hexStr) {
  xorKeyLen = 0;
  size_t len = strlen(hexStr);

  if (len % 2 != 0) return false;

  for (size_t i = 0; i < len; i += 2) {
    int hi = hexValue(hexStr[i]);
    int lo = hexValue(hexStr[i + 1]);
    if (hi < 0 || lo < 0) return false;
    xorKey[xorKeyLen++] = (uint8_t)((hi << 4) | lo);
  }

  return xorKeyLen > 0;
}

char nibbleToHex(uint8_t n) {
  if (n < 10) return '0' + n;
  return 'A' + (n - 10);
}

String xorEncodeToHex(const String& plainText) {
  String out = "";
  out.reserve(plainText.length() * 2);

  for (size_t i = 0; i < plainText.length(); i++) {
    uint8_t b = (uint8_t)plainText[i];
    uint8_t x = b ^ xorKey[i % xorKeyLen];
    out += nibbleToHex((x >> 4) & 0x0F);
    out += nibbleToHex(x & 0x0F);
  }
  return out;
}

// ---------- OLED ----------
void showText(String l1, String l2 = "", String l3 = "", String l4 = "", String l5 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  display.println(l1);
  if (l2.length()) display.println(l2);
  if (l3.length()) display.println(l3);
  if (l4.length()) display.println(l4);
  if (l5.length()) display.println(l5);

  display.display();
}

void showData(float temp, float hum, int eco2, int tvoc, int aqi) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  display.print("T: ");
  display.print(temp, 1);
  display.println(" C");

  display.print("H: ");
  display.print(hum, 1);
  display.println(" %");

  display.print("CO2: ");
  display.print(eco2);
  display.println(" ppm");

  display.print("TVOC:");
  display.print(tvoc);
  display.println(" ppb");

  display.print("AQI: ");
  display.println(aqi);

  display.display();
}

// ---------- WIFI ----------
void connectWiFi() {
  Serial.println("[WiFi] Connecting...");
  showText("WiFi", "Connecting...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 20) {
    delay(500);
    Serial.print(".");
    tries++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WiFi] Connected");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
    showText("WiFi Connected", WiFi.localIP().toString());
    delay(1500);
  } else {
    Serial.println("[WiFi] Failed");
    showText("WiFi Failed");
    delay(1500);
  }
}

// ---------- SENSORS ----------
void initSensors() {
  if (aht.begin()) {
    ahtReady = true;
    Serial.println("[OK] AHT ready");
  } else {
    Serial.println("[ERROR] AHT not found");
  }

  delay(500);

  ens160.begin();
  delay(1000);

  if (ens160.available()) {
    ens160.setMode(ENS160_OPMODE_STD);
    ensReady = true;
    Serial.println("[OK] ENS160 ready");
  } else {
    Serial.println("[ERROR] ENS160 not available");
  }
}

// ---------- API ----------
void sendToAPI(float temp, float hum, int eco2, int tvoc, int aqi, bool motion) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[API] WiFi not connected");
    return;
  }

  // Plain JSON first
  String plainJson = "{";
  plainJson += "\"temperature\":" + String(temp, 1) + ",";
  plainJson += "\"humidity\":" + String(hum, 1) + ",";
  plainJson += "\"co2\":" + String(eco2) + ",";
  plainJson += "\"tvoc\":" + String(tvoc) + ",";
  plainJson += "\"aqi\":" + String(aqi) + ",";
  plainJson += "\"motion\":";
  plainJson += (motion ? "true" : "false");
  plainJson += "}";

  // XOR encode -> HEX
  String encryptedHex = xorEncodeToHex(plainJson);

  // Envelope JSON sent to server
  String payload = "{";
  payload += "\"encoding\":\"xor-hex\",";
  payload += "\"data\":\"" + encryptedHex + "\"";
  payload += "}";

  Serial.println("----- TX DEBUG -----");
  Serial.println("Plain JSON:");
  Serial.println(plainJson);
  Serial.println("Encrypted HEX:");
  Serial.println(encryptedHex);
  Serial.println("--------------------");

  WiFiClientSecure client;
  HTTPClient http;

  // For easy testing with self-signed cert
  // For final project, better replace with setCACert(...)
  client.setInsecure();

  if (!http.begin(client, apiUrl)) {
    Serial.println("[API] HTTPS begin failed");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.setConnectTimeout(5000);
  http.setTimeout(5000);

  int code = http.POST(payload);

  Serial.print("[API] Response code: ");
  Serial.println(code);

  if (code == 200 || code == 201) {
    Serial.println("[API] Success");
    Serial.println(http.getString());
  } else if (code > 0) {
    Serial.println("[API] Server response:");
    Serial.println(http.getString());
  } else {
    Serial.print("[API] Error: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  if (!loadXorKey(XOR_KEY_HEX)) {
    Serial.println("[ERROR] Invalid XOR key");
    while (1) delay(100);
  }

  Wire.begin(SDA_PIN, SCL_PIN);
  pinMode(MOTION_PIN, INPUT);
  delay(500);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[ERROR] OLED not found");
    while (1) delay(100);
  }

  showText("Smart Home", "Starting...");
  delay(1000);

  initSensors();

  if (!ahtReady || !ensReady) {
    showText("Sensor Error");
    while (1) delay(100);
  }

  connectWiFi();

  showText("System Ready");
  delay(1500);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  unsigned long now = millis();
  bool motionDetected = digitalRead(MOTION_PIN) == HIGH;
  if (motionDetected) {
    motionActiveUntil = now + MOTION_HOLD_MS;
  }
  bool motionActive = motionDetected || (MOTION_HOLD_MS > 0 && (long)(motionActiveUntil - now) > 0);
  if (now - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = now;

    sensors_event_t humidityEvent, tempEvent;
    aht.getEvent(&humidityEvent, &tempEvent);

    float temperature = tempEvent.temperature;
    float humidity = humidityEvent.relative_humidity;

    if (ens160.available()) {
      ens160.measure(true);
    }

    int aqi = ens160.getAQI();
    int tvoc = ens160.getTVOC();
    int eco2 = ens160.geteCO2();

    Serial.println("----- SENSOR DATA -----");
    Serial.print("Temp: "); Serial.println(temperature, 1);
    Serial.print("Humidity: "); Serial.println(humidity, 1);
    Serial.print("CO2: "); Serial.println(eco2);
    Serial.print("TVOC: "); Serial.println(tvoc);
    Serial.print("AQI: "); Serial.println(aqi);
    Serial.print("Motion: "); Serial.println(motionActive ? "Detected" : "None");
    Serial.println("-----------------------");

    showData(temperature, humidity, eco2, tvoc, aqi);
    sendToAPI(temperature, humidity, eco2, tvoc, aqi, motionActive);
  }
}