# API Documentation - Smart Home Air Quality

Complete reference for all API endpoints and data formats.

## Base URL

```
https://localhost:8443
```

Note: TLS is required. If you use a self-signed certificate, pass `--cacert certs/server.crt`
to curl or configure your client to trust the CA.

## Authentication

No authentication required for current version (development mode).

**For production:** Add Bearer token or API key authentication.

---

## Endpoints

### 1. Health Check

**GET** `/api/health`

Check API and database status.

#### Response (200 OK)
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2024-04-29T15:30:45.123456Z"
}
```

#### Response (503 Service Unavailable)
```json
{
  "status": "ok",
  "database": "offline",
  "timestamp": "2024-04-29T15:30:45.123456Z"
}
```

#### Example
```bash
curl https://localhost:8443/api/health
```

---

### 2. Submit Sensor Data

**POST** `/api/sensor-data`

Submit a new sensor reading from ESP32. Data is validated and stored.

#### Request Body

```json
{
  "temperature": 24.5,
  "humidity": 65.0,
  "co2": 450,
  "tvoc": 25,
  "aqi": 1
}
```

#### Validation Rules

| Field | Type | Min | Max | Notes |
|-------|------|-----|-----|-------|
| temperature | float | -40 | 100 | Celsius |
| humidity | float | 0 | 100 | Percentage |
| co2 | int | 0 | 20000 | ppm |
| tvoc | int | 0 | 60000 | ppb |
| aqi | int | 0 | 5 | Index (0=Good, 5=Hazardous) |

#### Response (201 Created)
```json
{
  "status": "ok",
  "id": "507f1f77bcf86cd799439011",
  "timestamp": "2024-04-29T15:30:45.123456Z"
}
```

#### Error Response (400 Bad Request)
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "temperature"],
      "msg": "Input should be less than or equal to 100",
      "input": 150.0
    }
  ]
}
```

#### Error Response (503 Service Unavailable)
```json
{
  "detail": "Database not available - running in offline mode"
}
```

#### Examples

**cURL:**
```bash
curl -X POST https://localhost:8443/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 24.5,
    "humidity": 65.0,
    "co2": 450,
    "tvoc": 25,
    "aqi": 1
  }'
```

**Python:**
```python
import requests

data = {
    "temperature": 24.5,
    "humidity": 65.0,
    "co2": 450,
    "tvoc": 25,
    "aqi": 1
}

response = requests.post("https://localhost:8443/api/sensor-data", json=data)
print(response.json())
```

**JavaScript:**
```javascript
const data = {
  temperature: 24.5,
  humidity: 65.0,
  co2: 450,
  tvoc: 25,
  aqi: 1
};

fetch('https://localhost:8443/api/sensor-data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
})
.then(r => r.json())
.then(console.log);
```

---

### 3. Get Latest Reading

**GET** `/api/sensor-data/latest`

Retrieve the most recent sensor reading.

#### Response (200 OK)
```json
{
  "id": "507f1f77bcf86cd799439011",
  "temperature": 24.5,
  "humidity": 65.0,
  "co2": 450,
  "tvoc": 25,
  "aqi": 1,
  "timestamp": "2024-04-29T15:30:45.123456Z"
}
```

#### Response (404 Not Found)
```json
{
  "detail": "No sensor data available yet"
}
```

#### Examples

**cURL:**
```bash
curl https://localhost:8443/api/sensor-data/latest
```

**Python:**
```python
import requests

response = requests.get("https://localhost:8443/api/sensor-data/latest")
data = response.json()
print(f"Temperature: {data['temperature']}°C")
```

---

### 4. Get Sensor Data History

**GET** `/api/sensor-data`

Retrieve paginated history of sensor readings in chronological order.

#### Query Parameters

| Parameter | Type | Default | Min | Max | Description |
|-----------|------|---------|-----|-----|-------------|
| limit | int | 100 | 1 | 1000 | Number of records to return |

#### Response (200 OK)
```json
[
  {
    "id": "507f1f77bcf86cd799439010",
    "temperature": 23.8,
    "humidity": 64.5,
    "co2": 448,
    "tvoc": 24,
    "aqi": 1,
    "timestamp": "2024-04-29T15:20:00.000000Z"
  },
  {
    "id": "507f1f77bcf86cd799439011",
    "temperature": 24.5,
    "humidity": 65.0,
    "co2": 450,
    "tvoc": 25,
    "aqi": 1,
    "timestamp": "2024-04-29T15:30:45.123456Z"
  }
]
```

#### Response (404 Not Found)
```json
[]
```

#### Examples

**Get last 50 readings:**
```bash
curl "https://localhost:8443/api/sensor-data?limit=50"
```

**Get all available data (max 1000):**
```bash
curl "https://localhost:8443/api/sensor-data?limit=1000"
```

**Python:**
```python
import requests

response = requests.get("https://localhost:8443/api/sensor-data?limit=24")
readings = response.json()

for reading in readings:
    print(f"{reading['timestamp']}: {reading['temperature']}°C")
```

---

### 5. Get Statistics

**GET** `/api/sensor-data/stats`

Get aggregated statistics for sensor data over a time period.

#### Query Parameters

| Parameter | Type | Default | Min | Max | Description |
|-----------|------|---------|-----|-----|-------------|
| hours | int | 24 | 1 | 720 | Period in hours to analyze |

#### Response (200 OK)
```json
{
  "period_hours": 24,
  "record_count": 96,
  "temperature": {
    "min": 22.1,
    "max": 28.3,
    "avg": 25.2
  },
  "humidity": {
    "min": 45.0,
    "max": 78.5,
    "avg": 62.3
  },
  "co2": {
    "min": 380,
    "max": 550,
    "avg": 462
  }
}
```

#### Error Response (404 Not Found)
```json
{
  "detail": "No data available for the last 24 hours"
}
```

#### Examples

**Last 24 hours:**
```bash
curl "https://localhost:8443/api/sensor-data/stats?hours=24"
```

**Last 7 days:**
```bash
curl "https://localhost:8443/api/sensor-data/stats?hours=168"
```

**Last 30 days:**
```bash
curl "https://localhost:8443/api/sensor-data/stats?hours=720"
```

---

## Data Models

### SensorReading (Request)
```json
{
  "temperature": 24.5,
  "humidity": 65.0,
  "co2": 450,
  "tvoc": 25,
  "aqi": 1
}
```

### SensorReadingResponse (Response)
```json
{
  "id": "507f1f77bcf86cd799439011",
  "temperature": 24.5,
  "humidity": 65.0,
  "co2": 450,
  "tvoc": 25,
  "aqi": 1,
  "timestamp": "2024-04-29T15:30:45.123456Z"
}
```

### HealthStatus
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2024-04-29T15:30:45.123456Z"
}
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET request |
| 201 | Created | Successful POST request |
| 400 | Bad Request | Invalid request data |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Internal server error |
| 503 | Service Unavailable | Database connection lost |

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Validation Errors
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "field_name"],
      "msg": "Error description",
      "input": "value_provided"
    }
  ]
}
```

---

## Rate Limiting

Current implementation has no rate limiting (development mode).

**For production:** Implement rate limiting to prevent abuse.

Suggested limits:
- 1000 requests per hour per IP
- 60 requests per minute for POST /api/sensor-data
- 100 requests per minute for GET endpoints

---

## CORS (Cross-Origin Resource Sharing)

All endpoints accept requests from any origin (*)

**For production:** Restrict to specific domains:
```python
allow_origins=["https://yourdomain.com"]
```

---

## Example API Workflows

### Workflow 1: ESP32 Sending Data (Every 15 seconds)

```
1. ESP32 reads sensors
2. ESP32 formats JSON: {temp, humidity, co2, tvoc, aqi}
3. ESP32 HTTPS POST to /api/sensor-data
4. API validates data
5. API stores in MongoDB
6. API returns 201 with document ID
7. ESP32 displays "Success" on OLED
```

### Workflow 2: Dashboard Fetching Data (Every 10 seconds)

```
1. JavaScript calls /api/sensor-data/latest
2. API queries MongoDB for newest document
3. API returns latest reading
4. JavaScript updates display values
5. JavaScript calls /api/sensor-data?limit=120
6. API queries MongoDB for last 120 readings
7. API returns array in chronological order
8. JavaScript updates chart with new data
```

### Workflow 3: Analytics Query (On-demand)

```
1. User clicks "Statistics" button
2. JavaScript calls /api/sensor-data/stats?hours=24
3. API calculates min/max/avg for last 24 hours
4. API returns aggregated data
5. JavaScript displays statistics
```

---

## Testing

### Manual Testing with cURL

```bash
# 1. Check health
curl https://localhost:8443/api/health

# 2. Submit test data
curl -X POST https://localhost:8443/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"temperature":23.5,"humidity":60,"co2":400,"tvoc":20,"aqi":0}'

# 3. Get latest
curl https://localhost:8443/api/sensor-data/latest

# 4. Get history
curl https://localhost:8443/api/sensor-data?limit=10

# 5. Get stats
curl https://localhost:8443/api/sensor-data/stats?hours=24
```

### Automated Testing with Python

```python
import requests
import json
from datetime import datetime

BASE_URL = "https://localhost:8443"

def test_api():
    # Test health
    r = requests.get(f"{BASE_URL}/api/health")
    print("Health:", r.json())
    
    # Test submit
    data = {
        "temperature": 25.0,
        "humidity": 60.0,
        "co2": 450,
        "tvoc": 30,
        "aqi": 1
    }
    r = requests.post(f"{BASE_URL}/api/sensor-data", json=data)
    print("Submit:", r.json())
    
    # Test latest
    r = requests.get(f"{BASE_URL}/api/sensor-data/latest")
    print("Latest:", r.json())
    
    # Test history
    r = requests.get(f"{BASE_URL}/api/sensor-data?limit=10")
    print("History:", len(r.json()), "readings")
    
    # Test stats
    r = requests.get(f"{BASE_URL}/api/sensor-data/stats?hours=24")
    print("Stats:", r.json())

if __name__ == "__main__":
    test_api()
```

---

## Integration Examples

### Node.js / Express
```javascript
const axios = require('axios');

async function getSensorData() {
  try {
    const response = await axios.get('https://localhost:8443/api/sensor-data/latest');
    console.log(response.data);
  } catch (error) {
    console.error('Error:', error.message);
  }
}
```

### Python Requests
```python
import requests

response = requests.get('https://localhost:8443/api/sensor-data/latest')
if response.status_code == 200:
    print(response.json())
```

### React
```javascript
import { useState, useEffect } from 'react';

function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/sensor-data/latest')
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return data ? <div>{data.temperature}°C</div> : <div>Loading...</div>;
}
```

---

**API Version**: 1.0.0
**Last Updated**: April 2024
