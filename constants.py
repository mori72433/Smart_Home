"""
Configuration file for Smart Home Air Quality Dashboard
"""

# MongoDB Connection
MONGO_URI = "mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/"
# mongodb+srv uses TLS by default.
MONGO_DB = "smarthome"

# ===== ORGANIZED COLLECTIONS =====
MONGO_COLLECTION = "readings"                    # All sensor data (primary)
MONGO_COLLECTION_TEMP = "temperature_humidity"  # Temperature & Humidity only
MONGO_COLLECTION_AQI = "air_quality"             # CO2, TVOC, AQI only

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 443
API_WORKERS = 1

# Data Validation
TEMP_MIN = -40
TEMP_MAX = 100
HUMIDITY_MIN = 0
HUMIDITY_MAX = 100
CO2_MIN = 0
CO2_MAX = 20000
TVOC_MIN = 0
TVOC_MAX = 60000
AQI_MIN = 0
AQI_MAX = 5

# API Limits
MAX_SENSOR_DATA_LIMIT = 1000
DEFAULT_DATA_LIMIT = 100
DATA_RETENTION_DAYS = 90  # Keep data for 90 days

# XOR payload encoding (hex bytes, no 0x prefix)
XOR_KEY_HEX = "A1B2C3D4"

# Sensor Configuration
SENSOR_READ_INTERVAL_MS = 5000  # 5 seconds
SENSOR_SEND_INTERVAL_MS = 5000  # 5 seconds