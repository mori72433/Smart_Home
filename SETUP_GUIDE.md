# Smart Home Air Quality Dashboard - Complete Setup Guide

## Quick Start (5 Minutes)

### Step 1: Configure & Start Backend
```bash
cd /home/akai/Downloads/Smart\ Home

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set MongoDB connection
export MONGO_URI="mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"

# Create TLS certificate (local network)
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -keyout certs/server.key -out certs/server.crt -days 365 -subj "/CN=YOUR_SERVER_IP"

# Start API server (HTTPS/TLS)
python -m uvicorn app:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

You should see:
```
[DB] Successfully connected to MongoDB: smarthome.readings
INFO:     Uvicorn running on https://0.0.0.0:8443
```

### Step 2: Configure & Upload Arduino Code
1. Open `ardiuno.ino` in Arduino IDE
2. Update WiFi settings:
   ```cpp
   const char* ssid = "YOUR_SSID";
   const char* password = "YOUR_PASSWORD";
   const char* apiUrl = "https://192.168.x.x:8443/api/sensor-data";  // Your PC IP

   const char* rootCa =
   "-----BEGIN CERTIFICATE-----\n"
   "PASTE_YOUR_CA_CERTIFICATE_HERE\n"
   "-----END CERTIFICATE-----\n";
   ```
3. Install required libraries:
   - Adafruit_GFX
   - Adafruit_SSD1306
   - Adafruit_AHTX0
   - ScioSense_ENS160
   - ArduinoJson

4. Connect ESP32 to computer and upload

### Step 3: View Dashboard
Open browser: `https://192.168.x.x:8443`

---

## Detailed Setup Instructions

### Part 1: MongoDB Setup

#### Option A: MongoDB Atlas (Recommended)
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free account
3. Create cluster (M0 free tier is fine)
4. Create database user:
   - Go to Database Access
   - Add User: `admin` / `admin12345`
5. Get connection string:
   - Go to Connect
   - Copy connection string
   - Format: `mongodb+srv://admin:admin12345@cluster0.xxxxx.mongodb.net/`

#### Option B: Local MongoDB
```bash
# Install MongoDB
# Then start local MongoDB server
mongod --dbpath /path/to/data

# Connection string:
MONGO_URI="mongodb://localhost:27017/"
```

### Part 2: Backend (Server & API)

#### System Requirements
- Python 3.10 or higher
- pip package manager
- Internet connection

#### Installation Steps

```bash
# 1. Navigate to project directory
cd /home/akai/Downloads/Smart\ Home

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
# Linux/Mac:
source venv/bin/activate

# Windows Command Prompt:
venv\Scripts\activate

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# 4. Install requirements
pip install -r requirements.txt

# 5. Verify installation
pip list
```

Expected packages:
- fastapi==0.115.0
- uvicorn[standard]==0.30.6
- pymongo==4.8.0
- pydantic==2.9.1
- python-dotenv==1.0.1

#### Configuration

Edit `constants.py`:
```python
MONGO_URI = "mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"
MONGO_DB = "smarthome"
MONGO_COLLECTION = "readings"
```

Or set environment variable:
```bash
# Linux/Mac
export MONGO_URI="mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"

# Windows PowerShell
$env:MONGO_URI="mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"

# Windows Command Prompt
set MONGO_URI=mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/
```

#### Start Server

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

Advanced options:
```bash
# Auto-reload on changes (development)
python -m uvicorn app:app --host 0.0.0.0 --port 8443 --reload --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt

# Debug logging
python -m uvicorn app:app --host 0.0.0.0 --port 8443 --log-level debug --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt

# Multiple workers (production)
python -m uvicorn app:app --host 0.0.0.0 --port 8443 --workers 4 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

Verify server is running:
```bash
curl https://localhost:8443/api/health --cacert certs/server.crt
```

Response:
```json
{"status":"ok","database":"connected","timestamp":"2024-04-29T..."}
```

### Part 3: Arduino/ESP32

#### Hardware Connections

ESP32 Pin Layout (DevKit):
```
ESP32 Pin    Sensor Pin    Wire Color
21 (SDA)  ← SDA (AHT/ENS)  Yellow
22 (SCL)  ← SCL (AHT/ENS)  Green
3.3V      ← VCC             Red
GND       ← GND             Black
```

Display (SSD1306):
- SDA → GPIO 21
- SCL → GPIO 22
- VCC → 3.3V
- GND → GND

#### Arduino IDE Setup

1. **Install ESP32 Board Support**
   - File → Preferences
   - Add URL: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Tools → Board → Boards Manager
   - Search "ESP32" → Install

2. **Select Board**
   - Tools → Board → ESP32 → DEVKIT V1

3. **Install Required Libraries**
   - Tools → Manage Libraries
   - Search and install each:
     - "Adafruit GFX Library" (by Adafruit)
     - "Adafruit SSD1306" (by Adafruit)
     - "Adafruit AHTX0" (by Adafruit)
     - "ScioSense ENS160" (by ScioSense)
     - "ArduinoJson" (by Benoit Blanchon)

#### Configuration

Open `ardiuno.ino` and update:

```cpp
// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// API endpoint (use your PC's IP address on local network)
// Find IP with: ipconfig (Windows) or hostname -I (Linux)
const char* apiUrl = "https://192.168.1.100:8443/api/sensor-data";

const char* rootCa =
"-----BEGIN CERTIFICATE-----\n"
"PASTE_YOUR_CA_CERTIFICATE_HERE\n"
"-----END CERTIFICATE-----\n";
```

#### Upload

1. Connect ESP32 via USB
2. Tools → Port → Select COM port
3. Sketch → Upload (or Ctrl+U)
4. Monitor output: Tools → Serial Monitor (115200 baud)

Expected output:
```
===== ESP32 Smart Home Sensor System =====
Initializing...

[OK] OLED display initialized
[OK] AHT temperature/humidity sensor initialized
[OK] ENS160 air quality sensor initialized
[WiFi] Attempting connection...
[WiFi] Connected! IP: 192.168.1.50
===== System Ready =====

===== SENSOR READING #1 =====
[Temp] 24.5 °C
[Hum]  65.3 %
[CO2] 450 ppm
[TVOC] 25 ppb
[AQI]  1
[API] Sending: {"temperature":24.5,...}
[API] Success (200): {"status":"ok",...}
```

### Part 4: Dashboard Access

1. **Local Network**
   ```
   https://192.168.1.100:8443
   ```

2. **Same Computer**
   ```
   https://localhost:8443
   ```

3. **Mobile on Same Network**
   ```
   https://192.168.1.100:8443
   ```

### Part 5: Verify Everything Works

1. **Check Backend**
   ```bash
   curl https://localhost:8443/api/health --cacert certs/server.crt
   ```

2. **Check Latest Data**
   ```bash
   curl https://localhost:8443/api/sensor-data/latest --cacert certs/server.crt
   ```

3. **View Dashboard**
   - Open browser to `https://localhost:8443`
   - Should show "Live" status
   - Values should update every 10 seconds

---

## Troubleshooting

### ESP32 Connection Issues

**Problem**: "Connecting..." repeatedly
```
Solution:
1. Verify WiFi SSID and password (case-sensitive)
2. Check if 2.4GHz band is enabled (ESP32 doesn't support 5GHz)
3. Move ESP32 closer to router
4. Restart router
```

**Problem**: Cannot reach API from ESP32
```
Solution:
1. Verify API server is running: curl https://localhost:8443/api/health --cacert certs/server.crt
2. Check PC firewall allows port 8443
3. Verify both devices on same WiFi network
4. Check API URL in ardiuno.ino has correct IP address
5. Run: ipconfig (Windows) or hostname -I (Linux) to find PC IP
```

### Database Connection Issues

**Problem**: "MONGO_URI not set"
```
Solution:
1. Add to constants.py:
   MONGO_URI = "mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"
   
2. OR set environment variable:
   export MONGO_URI="mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"
```

**Problem**: Database connection timeout
```
Solution:
1. Check MongoDB cluster is running
2. Verify connection string is correct
3. Check IP whitelist in MongoDB Atlas (allow 0.0.0.0/0 for development)
4. Verify internet connection
```

### Dashboard Issues

**Problem**: Dashboard shows "Waiting for data..."
```
Solution:
1. Check server status: curl https://localhost:8443/api/health --cacert certs/server.crt
2. Check browser console (F12 → Console tab) for errors
3. Verify ESP32 is actually sending data (check serial monitor)
4. Check firewall allows port 8443
```

**Problem**: Chart not showing data
```
Solution:
1. Wait 2-3 minutes for ESP32 to collect multiple readings
2. Check MongoDB contains data via MongoDB Compass
3. Verify /api/sensor-data endpoint returns data:
   curl https://localhost:8443/api/sensor-data --cacert certs/server.crt
```

### Serial Monitor Output Issues

**Problem**: No output in serial monitor
```
Solution:
1. Verify correct COM port selected
2. Set baud rate to 115200
3. Check USB cable is properly connected
4. Try different USB port
5. Reinstall CH340 drivers (common ESP32 USB driver)
```

---

## Testing Checklist

- [ ] Backend server starts successfully
- [ ] MongoDB connection shows "[DB] Successfully connected"
- [ ] Can access https://localhost:8443 in browser
- [ ] ESP32 connects to WiFi (shows "WiFi Connected" in serial)
- [ ] ESP32 reads sensors (see temperature, humidity, CO2 values)
- [ ] ESP32 successfully sends to API ("[API] Success (200)")
- [ ] Dashboard shows "Live" status
- [ ] Dashboard displays sensor values
- [ ] Chart appears and updates every 10 seconds
- [ ] Multiple readings appear in database

---

## Next Steps

Once everything is working:

1. **Deploy to Cloud** (Optional)
   - Upload backend to AWS, Google Cloud, or Heroku
   - Update ESP32 API URL to cloud endpoint
   - Enable HTTPS for security

2. **Add More Features**
   - Alerts for poor air quality
   - Data export to CSV
   - Multiple device support
   - Mobile app

3. **Optimize**
   - Adjust sensor read intervals
   - Implement data averaging
   - Add caching

---

## Support Resources

- [MongoDB Atlas Guide](https://docs.mongodb.com/cloud/atlas/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Arduino ESP32 Guide](https://docs.espressif.com/projects/arduino-esp32/)
- [Sensor Datasheets](https://www.adafruit.com)

---

**Good luck with your project!** 🎉
