#!/usr/bin/env python3
"""
Export sensor data from MongoDB to organized CSV files.
Run: python3 export_data.py

Exports all three collections to separate, organized CSV files:
  - data/readings_all.csv (complete sensor data)
  - data/temperature_humidity.csv (temperature & humidity)
  - data/air_quality.csv (CO2, TVOC, AQI)
  - data/summary.txt (statistics and export info)
"""

import os
import csv
from datetime import datetime
from pymongo import MongoClient, DESCENDING

try:
    from constants import (
        MONGO_URI, MONGO_DB, MONGO_COLLECTION,
        MONGO_COLLECTION_TEMP, MONGO_COLLECTION_AQI
    )
except Exception:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin12345@cluster0.dujlamb.mongodb.net/")
    MONGO_DB = "smarthome"
    MONGO_COLLECTION = "readings"
    MONGO_COLLECTION_TEMP = "temperature_humidity"
    MONGO_COLLECTION_AQI = "air_quality"

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

# Connect to MongoDB
print(f"[Export] Connecting to MongoDB...")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    print("✓ Connected to MongoDB")
except Exception as e:
    print(f"✗ MongoDB connection failed: {e}")
    exit(1)

db = client[MONGO_DB]

# Export function
def export_collection(collection_name, filename, fields):
    """Export collection to CSV with specified fields"""
    collection = db[collection_name]
    docs = list(collection.find().sort("timestamp", DESCENDING))
    
    if not docs:
        print(f"  ⚠ No data in collection '{collection_name}'")
        return 0
    
    print(f"  [*] Exporting {len(docs)} documents from '{collection_name}' to '{filename}'...")
    
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for doc in reversed(docs):
            row = []
            for field in fields:
                if field == "Timestamp":
                    ts = doc.get("timestamp")
                    row.append(ts.isoformat() if ts else "")
                elif field == "Temperature(°C)":
                    row.append(doc.get("temperature"))
                elif field == "Humidity(%)":
                    row.append(doc.get("humidity"))
                elif field == "CO2(ppm)":
                    row.append(doc.get("co2"))
                elif field == "TVOC(ppb)":
                    row.append(doc.get("tvoc"))
                elif field == "AQI":
                    row.append(doc.get("aqi"))
                elif field == "Motion":
                    motion_value = doc.get("motion")
                    if motion_value is None:
                        row.append("")
                    else:
                        row.append(int(bool(motion_value)))
            writer.writerow(row)
    
    return len(docs)

# Export all collections
print("\n[Export] Starting data exports...\n")
print("1️⃣  Exporting all sensor data:")
count_all = export_collection(
    MONGO_COLLECTION,
    "data/readings_all.csv",
    [
        "Timestamp",
        "Temperature(°C)",
        "Humidity(%)",
        "CO2(ppm)",
        "TVOC(ppb)",
        "AQI",
        "Motion",
    ]
)

print("\n2️⃣  Exporting temperature & humidity data:")
count_temp = export_collection(
    MONGO_COLLECTION_TEMP,
    "data/temperature_humidity.csv",
    ["Timestamp", "Temperature(°C)", "Humidity(%)"]
)

print("\n3️⃣  Exporting air quality data:")
count_aqi = export_collection(
    MONGO_COLLECTION_AQI,
    "data/air_quality.csv",
    ["Timestamp", "CO2(ppm)", "TVOC(ppb)", "AQI"]
)

# Write summary
print("\n📊 Creating summary...")
summary_text = f"""
SMART HOME SENSOR DATA EXPORT SUMMARY
Generated: {datetime.now().isoformat()}

Collections:
  - readings (all data): {count_all} records
  - temperature_humidity: {count_temp} records
  - air_quality: {count_aqi} records

Files created:
  ✓ data/readings_all.csv (complete sensor readings)
  ✓ data/temperature_humidity.csv (temperature & humidity only)
  ✓ data/air_quality.csv (CO2, TVOC, AQI only)

Data Range:
  Total Records: {max(count_all, count_temp, count_aqi)}
  Collections: {MONGO_DB} ({MONGO_COLLECTION}, {MONGO_COLLECTION_TEMP}, {MONGO_COLLECTION_AQI})
  Database URI: {MONGO_URI.split('@')[0]}...@...

How to use:
  - Open CSV files with Excel, Google Sheets, or Python pandas
  - Import into data analysis tools (matplotlib, BI tools, etc.)
  - Run export_data.py anytime to get the latest readings
"""

with open("data/summary.txt", "w") as f:
    f.write(summary_text)

print(summary_text)
print("\n✓ Export complete!")

