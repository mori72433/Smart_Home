import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo import DESCENDING, MongoClient
from pymongo.errors import ServerSelectionTimeoutError

try:
    from constants import (
        MONGO_URI as DEFAULT_MONGO_URI,
        MONGO_DB,
        MONGO_COLLECTION,
        MONGO_COLLECTION_TEMP,
        MONGO_COLLECTION_AQI,
        TEMP_MIN,
        TEMP_MAX,
        HUMIDITY_MIN,
        HUMIDITY_MAX,
        CO2_MIN,
        CO2_MAX,
        TVOC_MIN,
        TVOC_MAX,
        AQI_MIN,
        AQI_MAX,
        MAX_SENSOR_DATA_LIMIT,
        DEFAULT_DATA_LIMIT,
    )
except Exception:
    DEFAULT_MONGO_URI = None
    MONGO_DB = "smarthome"
    MONGO_COLLECTION = "readings"
    TEMP_MIN, TEMP_MAX = -40, 100
    HUMIDITY_MIN, HUMIDITY_MAX = 0, 100
    CO2_MIN, CO2_MAX = 0, 20000
    TVOC_MIN, TVOC_MAX = 0, 60000
    AQI_MIN, AQI_MAX = 0, 5
    MAX_SENSOR_DATA_LIMIT = 1000
    DEFAULT_DATA_LIMIT = 100

MONGO_URI = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set. Set environment variable or update constants.py")

# ===== MONGODB SETUP =====
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Verify connection
    db = client[MONGO_DB]
    
    # Primary collection (all data)
    collection = db[MONGO_COLLECTION]
    collection.create_index([("timestamp", DESCENDING)])
    
    # Secondary collections (organized data)
    collection_temp = db[MONGO_COLLECTION_TEMP]
    collection_temp.create_index([("timestamp", DESCENDING)])
    
    collection_aqi = db[MONGO_COLLECTION_AQI]
    collection_aqi.create_index([("timestamp", DESCENDING)])
    
    print(f"[DB] Successfully connected to MongoDB: {MONGO_DB}.{MONGO_COLLECTION}")
    print(f"[DB] Collections: {MONGO_COLLECTION} (all), {MONGO_COLLECTION_TEMP} (temp), {MONGO_COLLECTION_AQI} (air quality)")
except ServerSelectionTimeoutError as e:
    print(f"[DB] MongoDB connection failed: {e}")
    print("[DB] Running in offline mode - data will not persist")
    collection = None
    collection_temp = None
    collection_aqi = None

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# ===== FASTAPI SETUP =====
app = FastAPI(
    title="Smart Home Air Quality API",
    description="Real-time environmental sensor data collection and dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== DATA MODELS =====
class SensorReading(BaseModel):
    """Sensor reading data model with validation"""
    temperature: float = Field(
        ..., ge=TEMP_MIN, le=TEMP_MAX, description="Temperature in Celsius"
    )
    humidity: float = Field(
        ..., ge=HUMIDITY_MIN, le=HUMIDITY_MAX, description="Humidity percentage"
    )
    co2: int = Field(..., ge=CO2_MIN, le=CO2_MAX, description="CO2 in ppm")
    tvoc: int = Field(..., ge=TVOC_MIN, le=TVOC_MAX, description="TVOC in ppb")
    aqi: int = Field(..., ge=AQI_MIN, le=AQI_MAX, description="Air Quality Index")

    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 24.5,
                "humidity": 65.0,
                "co2": 450,
                "tvoc": 25,
                "aqi": 1,
            }
        }


class SensorReadingResponse(SensorReading):
    """Response model with ID and timestamp"""
    id: str = Field(..., description="MongoDB document ID")
    timestamp: str = Field(..., description="ISO format timestamp")


class HealthStatus(BaseModel):
    """System health status"""
    status: str
    database: str
    timestamp: str


# ===== HELPER FUNCTIONS =====
def serialize_reading(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    return {
        "id": str(doc.get("_id")),
        "temperature": doc.get("temperature"),
        "humidity": doc.get("humidity"),
        "co2": doc.get("co2"),
        "tvoc": doc.get("tvoc"),
        "aqi": doc.get("aqi"),
        "timestamp": doc.get("timestamp").isoformat()
        if doc.get("timestamp")
        else None,
    }


# ===== API ROUTES =====
@app.get("/", tags=["UI"])
def get_index():
    """Serve dashboard UI"""
    return FileResponse(str(STATIC_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health", response_model=HealthStatus, tags=["System"])
def health_check():
    """Check API and database health status"""
    db_status = "connected"
    if collection is None:
        db_status = "offline"
    
    return HealthStatus(
        status="ok",
        database=db_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/api/sensor-data",
    response_model=dict,
    tags=["Sensor Data"],
    status_code=201,
)
def add_sensor_data(reading: SensorReading):
    """
    Record new sensor reading from ESP32.
    
    Receives:
    - temperature (°C)
    - humidity (%)
    - co2 (ppm)
    - tvoc (ppb)
    - aqi (index 0-5)
    """
    if collection is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available - running in offline mode",
        )

    try:
        doc = reading.model_dump()
        doc["timestamp"] = datetime.now(timezone.utc)
        
        # Write to all three collections
        result_full = collection.insert_one(doc)
        
        # Temperature & Humidity subset
        doc_temp = {
            "temperature": doc["temperature"],
            "humidity": doc["humidity"],
            "timestamp": doc["timestamp"],
        }
        collection_temp.insert_one(doc_temp)
        
        # Air Quality subset
        doc_aqi = {
            "co2": doc["co2"],
            "tvoc": doc["tvoc"],
            "aqi": doc["aqi"],
            "timestamp": doc["timestamp"],
        }
        collection_aqi.insert_one(doc_aqi)
        
        print(
            f"[API] Sensor data recorded (ID: {result_full.inserted_id}): "
            f"T={reading.temperature}°C, H={reading.humidity}%, "
            f"CO2={reading.co2}ppm, TVOC={reading.tvoc}ppb, AQI={reading.aqi}"
        )
        
        return {
            "status": "ok",
            "id": str(result_full.inserted_id),
            "timestamp": doc["timestamp"].isoformat(),
        }
    except Exception as e:
        print(f"[API] Error saving sensor data: {e}")
        raise HTTPException(status_code=500, detail="Error saving sensor data")


@app.get(
    "/api/sensor-data/latest",
    response_model=SensorReadingResponse,
    tags=["Sensor Data"],
)
def get_latest_sensor_data():
    """Get the most recent sensor reading"""
    if collection is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available",
        )

    doc = collection.find_one(sort=[("timestamp", DESCENDING)])
    if not doc:
        raise HTTPException(status_code=404, detail="No sensor data available yet")
    
    return serialize_reading(doc)


@app.get(
    "/api/sensor-data",
    response_model=list[SensorReadingResponse],
    tags=["Sensor Data"],
)
def list_sensor_data(
    limit: int = Query(
        DEFAULT_DATA_LIMIT, ge=1, le=MAX_SENSOR_DATA_LIMIT, description="Number of records"
    )
):
    """
    Get sensor data history.
    
    Returns data in chronological order (oldest to newest).
    """
    if collection is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available",
        )

    try:
        docs = list(
            collection.find().sort("timestamp", DESCENDING).limit(limit)
        )
        
        if not docs:
            return []
        
        docs.reverse()
        return [serialize_reading(doc) for doc in docs]
    except Exception as e:
        print(f"[API] Error fetching sensor data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching data")


@app.get("/api/sensor-data/stats", tags=["Sensor Data"])
def get_sensor_stats(hours: int = Query(24, ge=1, le=720)):
    """Get statistics for sensor data from the last N hours"""
    if collection is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        docs = list(collection.find({"timestamp": {"$gte": since}}))
        
        if not docs:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for the last {hours} hours",
            )

        temps = [d.get("temperature") for d in docs if d.get("temperature")]
        humidities = [d.get("humidity") for d in docs if d.get("humidity")]
        co2s = [d.get("co2") for d in docs if d.get("co2")]

        return {
            "period_hours": hours,
            "record_count": len(docs),
            "temperature": {
                "min": min(temps) if temps else None,
                "max": max(temps) if temps else None,
                "avg": sum(temps) / len(temps) if temps else None,
            },
            "humidity": {
                "min": min(humidities) if humidities else None,
                "max": max(humidities) if humidities else None,
                "avg": sum(humidities) / len(humidities) if humidities else None,
            },
            "co2": {
                "min": min(co2s) if co2s else None,
                "max": max(co2s) if co2s else None,
                "avg": sum(co2s) / len(co2s) if co2s else None,
            },
        }
    except Exception as e:
        print(f"[API] Error calculating stats: {e}")
        raise HTTPException(status_code=500, detail="Error calculating statistics")
