import os
import base64
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
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
        XOR_KEY_HEX as DEFAULT_XOR_KEY_HEX,
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
    DEFAULT_XOR_KEY_HEX = "A1B2C3D4"

MONGO_URI = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set. Set environment variable or update constants.py")

XOR_KEY_HEX = os.getenv("XOR_KEY_HEX", DEFAULT_XOR_KEY_HEX)


def parse_xor_key(hex_string: str) -> bytes:
    cleaned = "".join(hex_string.split())
    if len(cleaned) % 2 != 0:
        raise ValueError("XOR key must have an even number of hex digits")
    return bytes.fromhex(cleaned)


def xor_decode_base64(payload_b64: str, key_bytes: bytes) -> dict:
    if not key_bytes:
        raise ValueError("XOR key is empty")

    try:
        encrypted = base64.b64decode(payload_b64)
    except Exception as exc:
        raise ValueError("Invalid base64 payload") from exc

    decoded_bytes = bytearray(len(encrypted))
    for idx, value in enumerate(encrypted):
        decoded_bytes[idx] = value ^ key_bytes[idx % len(key_bytes)]

    try:
        decoded_text = decoded_bytes.decode("utf-8")
        return json.loads(decoded_text)
    except Exception as exc:
        raise ValueError("Decoded payload is not valid JSON") from exc


def xor_decode_hex(hex_data: str, key_bytes: bytes) -> str:
    if not key_bytes:
        raise ValueError("XOR key is empty")

    cleaned = "".join(hex_data.split())
    if len(cleaned) % 2 != 0:
        raise ValueError("Hex payload must have an even number of digits")

    try:
        raw = bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError("Invalid hex payload") from exc

    decoded_bytes = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(raw))
    try:
        return decoded_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decoded payload is not valid UTF-8") from exc

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
    motion: bool | None = Field(
        default=None, description="Motion detected by PIR sensor"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 24.5,
                "humidity": 65.0,
                "co2": 450,
                "tvoc": 25,
                "aqi": 1,
                "motion": False,
            }
        }


class SensorReadingResponse(SensorReading):
    """Response model with ID and timestamp"""
    id: str = Field(..., description="MongoDB document ID")
    timestamp: str = Field(..., description="ISO format timestamp")


class XorPayload(BaseModel):
    """XOR-encoded payload wrapper"""
    encoding: str
    data: str


class HealthStatus(BaseModel):
    """System health status"""
    status: str
    database: str
    timestamp: str


class MotionEvent(BaseModel):
    """Motion event with timestamp"""
    id: str
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
        "motion": doc.get("motion"),
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
async def add_sensor_data(request: Request):
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
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be an object")

    if body.get("xor") is True:
        payload_b64 = body.get("payload")
        if not isinstance(payload_b64, str):
            raise HTTPException(status_code=400, detail="Missing XOR payload")

        try:
            key_bytes = parse_xor_key(XOR_KEY_HEX)
            body = xor_decode_base64(payload_b64, key_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    try:
        reading = SensorReading(**body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())

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


@app.post(
    "/api/sensor-data-xor",
    response_model=dict,
    tags=["Sensor Data"],
    status_code=201,
)
def add_sensor_data_xor(payload: XorPayload):
    """Record XOR-hex encoded sensor reading from ESP32."""
    if collection is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available - running in offline mode",
        )

    if payload.encoding.lower() != "xor-hex":
        raise HTTPException(status_code=400, detail="Unsupported encoding")

    try:
        key_bytes = parse_xor_key(XOR_KEY_HEX)
        decoded_json = xor_decode_hex(payload.data, key_bytes)
        print(f"[API] Encrypted HEX: {payload.data}")
        print(f"[API] Decoded JSON: {decoded_json}")
        data = json.loads(decoded_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Decoded payload is not valid JSON")

    try:
        reading = SensorReading(**data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())

    try:
        doc = reading.model_dump()
        doc["timestamp"] = datetime.now(timezone.utc)

        result_full = collection.insert_one(doc)

        doc_temp = {
            "temperature": doc["temperature"],
            "humidity": doc["humidity"],
            "timestamp": doc["timestamp"],
        }
        collection_temp.insert_one(doc_temp)

        doc_aqi = {
            "co2": doc["co2"],
            "tvoc": doc["tvoc"],
            "aqi": doc["aqi"],
            "timestamp": doc["timestamp"],
        }
        collection_aqi.insert_one(doc_aqi)

        print(
            f"[API] XOR sensor data recorded (ID: {result_full.inserted_id}): "
            f"T={reading.temperature}°C, H={reading.humidity}%, "
            f"CO2={reading.co2}ppm, TVOC={reading.tvoc}ppb, AQI={reading.aqi}"
        )

        return {
            "status": "ok",
            "id": str(result_full.inserted_id),
            "timestamp": doc["timestamp"].isoformat(),
        }
    except Exception as e:
        print(f"[API] Error saving XOR sensor data: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error decoding or saving sensor data",
        )


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


@app.get(
    "/api/motion-events",
    response_model=list[MotionEvent],
    tags=["Motion"],
)
def list_motion_events(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(
        DEFAULT_DATA_LIMIT, ge=1, le=MAX_SENSOR_DATA_LIMIT, description="Max events"
    ),
):
    """Get motion events from the last N hours"""
    if collection is None:
        raise HTTPException(status_code=503, detail="Database not available")

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        docs = list(
            collection.find(
                {"motion": True, "timestamp": {"$gte": since}}
            )
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        if not docs:
            return []

        docs.reverse()
        results = []
        for doc in docs:
            timestamp = doc.get("timestamp")
            if not timestamp:
                continue
            results.append(
                {
                    "id": str(doc.get("_id")),
                    "timestamp": timestamp.isoformat(),
                }
            )

        return results
    except Exception as e:
        print(f"[API] Error fetching motion events: {e}")
        raise HTTPException(status_code=500, detail="Error fetching motion data")


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
