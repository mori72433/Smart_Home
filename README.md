# Smart Home Air Quality Dashboard 🏠

A complete **IoT system** for real-time environmental monitoring using ESP32, sensors, and a cloud-based dashboard.

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Smart Home IoT System                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Sensor Layer]        [Device Layer]      [Network Layer]      │
│  ┌──────────────┐      ┌──────────────┐    ┌──────────────┐    │
│  │ • ENS160     │      │ • ESP32      │    │ • WiFi       │    │
│  │ • AHT21      │──→   │ • Processing │───→│ • HTTPS      │    │
│  │             │      │ • JSON Format│    │              │    │
│  └──────────────┘      └──────────────┘    └──────────────┘    │
│         ↓                    ↓                    ↓              │
│  Temperature, Humidity,     Collect Data        Send to API     │
│  CO2, TVOC, AQI            Format Data                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [API Layer] - FastAPI + MongoDB                          │  │
│  │ • Receive sensor data from ESP32                         │  │
│  │ • Validate data format & ranges                          │  │
│  │ • Store in database                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [Server/Database Layer] - MongoDB                        │  │
│  │ • Cloud-based data storage                               │  │
│  │ • Historical data retention                              │  │
│  │ • Query & analytics                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [Dashboard Layer] - Web UI                               │  │
│  │ • Live sensor values                                     │  │
│  │ • Real-time charts                                       │  │
│  │ • Historical trends                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### Hardware
- **ESP32** - Microcontroller with WiFi connectivity
- **ENS160** - Air quality sensor (CO2, TVOC, AQI)
- **AHT21** - Temperature & humidity sensor
- **SSD1306** - OLED display for local monitoring
- **PIR motion sensor** - Motion detection

### Software
- **Arduino Code** - ESP32 sensor reading & API communication
- **FastAPI Backend** - RESTful API for data management
- **MongoDB** - Cloud database for data storage
- **Web Dashboard** - Real-time data visualization

## Features

✅ **Real-time Monitoring** - Live sensor data updates every 10 seconds
✅ **Data Persistence** - All readings stored in MongoDB
✅ **Historical Charts** - Visualize trends over time
✅ **Error Handling** - Robust reconnection & offline support
✅ **Mobile Responsive** - Works on desktop and mobile
✅ **Statistics API** - Query aggregated data
✅ **OLED Display** - Local device status display
✅ **Night Motion Tracking** - Motion detections between 7:00 PM and 6:00 AM

## Sensor Data

Each reading contains:
- **Temperature**: -40°C to +100°C
- **Humidity**: 0% to 100%
- **CO2**: 0 to 20000 ppm
- **TVOC**: 0 to 60000 ppb
- **AQI**: 0-5 index
- **Motion**: true/false (PIR sensor)

## API Endpoints

### Health & Status
```
GET /api/health
```
Check API and database status.

### Sensor Data - Submit
```
POST /api/sensor-data

Body:
{
  "temperature": 24.5,
  "humidity": 65.0,
  "co2": 450,
  "tvoc": 25,
  "aqi": 1
}

Response (201):
{
  "status": "ok",
  "id": "507f1f77bcf86cd799439011",
  "timestamp": "2024-04-29T12:34:56.789Z"
}
```

### Sensor Data - Latest
```
GET /api/sensor-data/latest

Response (200):
{
  "id": "507f1f77bcf86cd799439011",
  "temperature": 24.5,
  "humidity": 65.0,
  "co2": 450,
  "tvoc": 25,
  "aqi": 1,
  "timestamp": "2024-04-29T12:34:56.789Z"
}
```

### Sensor Data - History
```
GET /api/sensor-data?limit=120

Parameters:
- limit: 1-1000 (default: 100)

Response (200):
[
  {
    "id": "507f1f77bcf86cd799439011",
    "temperature": 24.5,
    ...
  },
  ...
]
```

### Sensor Data - Statistics
```
GET /api/sensor-data/stats?hours=24

Parameters:
- hours: 1-720 (default: 24)

Response (200):
{
  "period_hours": 24,
  "record_count": 144,
  "temperature": {
    "min": 22.1,
    "max": 28.3,
    "avg": 25.2
  },
  ...
}
```

### Motion Events
```
GET /api/motion-events?hours=24&limit=1000

Response (200):
[
  {
    "id": "507f1f77bcf86cd799439022",
    "timestamp": "2024-04-29T21:12:07.000000Z"
  }
]
```

## Setup & Installation

### Prerequisites
- Python 3.10+
- Arduino IDE / PlatformIO
- MongoDB Atlas account
- ESP32 with WiFi
- Sensors: ENS160, AHT21, SSD1306

### 1. Backend Setup

#### Clone/Download the Project
```bash
cd /home/akai/Downloads/Smart\ Home
```

#### Create Virtual Environment
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Configure MongoDB
1. Sign up at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a cluster and database user
3. Get your connection string
4. Update `constants.py` or set environment variable:

```bash
# Linux/Mac
export MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/"

# Windows (Command Prompt)
set MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Windows (PowerShell)
$env:MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/"
```

#### TLS Certificates (required)
Create a TLS certificate for the API. For local network testing, generate a self-signed cert:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -keyout certs/server.key -out certs/server.crt -days 365 -subj "/CN=YOUR_SERVER_IP"
```

For a public domain, use Let's Encrypt and point to the issued key/cert files.

#### Start the API (HTTPS/TLS required)
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
```

Expected output:
```
INFO:     Uvicorn running on https://0.0.0.0:443
INFO:     [DB] Successfully connected to MongoDB: smarthome.readings
```

### 2. Arduino/ESP32 Setup

#### Install Arduino Libraries
```
- WiFi (built-in)
- HTTPClient (built-in)
- Wire (built-in)
- Adafruit_GFX
- Adafruit_SSD1306
- Adafruit_AHTX0
- ScioSense_ENS160
- ArduinoJson
```

In Arduino IDE: Sketch → Include Library → Manage Libraries

#### Update Configuration
Edit `ardiuno.ino`:
```cpp
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const char* apiUrl = "https://YOUR_SERVER_IP/api/sensor-data";

const char* rootCa =
"-----BEGIN CERTIFICATE-----\n"
"PASTE_YOUR_CA_CERTIFICATE_HERE\n"
"-----END CERTIFICATE-----\n";
```

Get your server IP:
```bash
# Linux/Mac
hostname -I

# Windows
ipconfig | findstr "IPv4"
```

#### Upload to ESP32
1. Select Board: Tools → Board → ESP32 → DEVKIT V1
2. Select Port: Tools → Port → COMx (Windows) or /dev/ttyUSBx (Linux)
3. Click Upload

Monitor output:
```
Sketch → Serial Monitor (115200 baud)
```

### 3. Dashboard Access

Open browser and navigate to:
```
https://YOUR_SERVER_IP
```

## File Structure

```
Smart Home/
├── app.py                 # FastAPI backend
├── ardiuno.ino           # ESP32 firmware
├── constants.py          # Configuration
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── static/
    ├── index.html        # Dashboard UI
    ├── app.js           # Frontend logic
    └── styles.css       # Styling
```

## Troubleshooting

### ESP32 Cannot Connect to WiFi
- [ ] Check SSID and password in `ardiuno.ino`
- [ ] Ensure ESP32 and router are on same network
- [ ] Check router's 2.4GHz band is enabled (ESP32 doesn't support 5GHz)
- [ ] Monitor serial output for errors

### API Returns 503 "Database not available"
- [ ] Check MongoDB URI in constants.py or environment
- [ ] Verify MongoDB cluster is running
- [ ] Check IP whitelist on MongoDB Atlas
- [ ] Verify username/password

### Dashboard Shows "Waiting for data..."
- [ ] Check API is running: `curl https://localhost/api/health --cacert certs/server.crt`
- [ ] Verify ESP32 is sending data (check serial monitor)
- [ ] Check browser console for errors (F12)
- [ ] Verify firewall allows port 443

### Sensor Data Not Displaying
- [ ] Check sensor connections (SDA/SCL pins)
- [ ] Monitor serial output for sensor errors
- [ ] Verify I2C addresses match code (0x3C for display, 0x53 for ENS160)

## Performance & Limits

- **Data transmission**: Every 5 seconds
- **Dashboard refresh**: Every 10 seconds
- **Historical data**: 120 samples displayed
- **Retention**: Configurable (default 90 days)
- **Max limit**: 1000 records per query

## Development

### Run with Debug Logging
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 443 --reload --log-level debug
```

### View MongoDB Data
```bash
# Using MongoDB Compass or Atlas UI
# Database: smarthome
# Collection: readings
```

### Modify Sensor Intervals
In `ardiuno.ino`:
```cpp
#define SEND_INTERVAL_MS 5000  // Change to desired milliseconds
```

## Security Notes

⚠️ **For Production Use:**
- HTTPS/TLS is required for all API traffic
- Add authentication to API endpoints
- Implement rate limiting
- Use secure WiFi credentials (not hardcoded)
- Enable MongoDB IP whitelist
- Use environment variables for secrets
- MongoDB Atlas uses TLS by default; enable TLS for local MongoDB deployments

## Future Enhancements

- [ ] Mobile app (React Native)
- [ ] Data export (CSV, JSON)
- [ ] Alert notifications
- [ ] Multi-device support
- [ ] Cloud deployment (AWS, Google Cloud)
- [ ] Advanced analytics

## License

This project is for educational purposes.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review serial monitor output
3. Check MongoDB connection
4. Verify all components are connected

---

**Created**: 2024
**Last Updated**: April 29, 2024

hellow friend
