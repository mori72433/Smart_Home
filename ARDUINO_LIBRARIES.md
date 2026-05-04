# Arduino Library Dependencies Reference

This document lists all Arduino libraries required for the ESP32 smart home sensor project.

## Required Libraries

### Core Libraries (Built-in ESP32)
- ✓ `WiFi.h` - WiFi connectivity
- ✓ `HTTPClient.h` - HTTP requests
- ✓ `Wire.h` - I2C communication

### External Libraries (Must Install)

#### Display
- **Adafruit_GFX** (by Adafruit Industries)
  - Version: 1.11.9+
  - Use for: Graphics library for displays
  - Install: Tools → Manage Libraries → Search "Adafruit GFX"

- **Adafruit_SSD1306** (by Adafruit Industries)
  - Version: 2.5.10+
  - Use for: SSD1306 OLED display control
  - Depends on: Adafruit_GFX
  - Install: Tools → Manage Libraries → Search "Adafruit SSD1306"

#### Sensors
- **Adafruit_AHTX0** (by Adafruit Industries)
  - Version: 1.2.0+
  - Use for: AHT21 temperature & humidity sensor
  - Install: Tools → Manage Libraries → Search "Adafruit AHTX0"

- **ScioSense_ENS160** (by ScioSense)
  - Version: 1.0.0+
  - Use for: ENS160 air quality sensor
  - Install: Tools → Manage Libraries → Search "ScioSense ENS160"

#### Data
- **ArduinoJson** (by Benoit Blanchon)
  - Version: 7.0.0+
  - Use for: JSON serialization (payload formatting)
  - Install: Tools → Manage Libraries → Search "ArduinoJson"

## Installation Instructions

### Via Arduino IDE

1. Open Arduino IDE
2. Go to **Tools → Manage Libraries**
3. For each library:
   - Type library name in search box
   - Click "Install"
   - Wait for installation to complete

### Installation Order (Recommended)
1. Adafruit_GFX (required by other libraries)
2. Adafruit_SSD1306
3. Adafruit_AHTX0
4. ScioSense_ENS160
5. ArduinoJson

### Verification

After installation, verify in Arduino IDE:
- Sketch → Include Library
- You should see all 5 external libraries listed

## Library Details

### Adafruit_GFX Library
```cpp
#include <Adafruit_GFX.h>
// Provides graphics primitives for any display
```

### Adafruit_SSD1306 Library
```cpp
#include <Adafruit_SSD1306.h>
// Requires: Adafruit_GFX
// Initialize: Adafruit_SSD1306 display(WIDTH, HEIGHT, &Wire, -1);
// Common I2C Address: 0x3C
```

### Adafruit_AHTX0 Library
```cpp
#include <Adafruit_AHTX0.h>
// Initialize: Adafruit_AHTX0 aht;
// Methods: aht.getEvent(&humidity, &temperature);
// I2C Address: 0x38 (auto)
```

### ScioSense_ENS160 Library
```cpp
#include <ScioSense_ENS160.h>
// Initialize: ScioSense_ENS160 ens160(0x53);
// Methods: ens160.measure(), ens160.getAQI(), etc.
// I2C Address: 0x53 (default)
```

### ArduinoJson Library
```cpp
#include <ArduinoJson.h>
// Usage: StaticJsonDocument<256> doc;
// serializeJson(doc, payload);
```

## Troubleshooting

### "No library found" Error
```
Solution:
1. Ensure internet connection
2. Try installing from different Arduino IDE instance
3. Check IDE version (1.8.13+)
4. Restart Arduino IDE
```

### Compilation Error: "Unknown identifier"
```
Solution:
1. Verify library is actually installed
2. Check #include statement spelling
3. Reinstall library
4. Check library version compatibility
```

### I2C Address Conflicts
```
ESP32 I2C Default Addresses:
- SSD1306 Display: 0x3C
- AHT21 Sensor: 0x38
- ENS160 Sensor: 0x53

If conflict occurs:
1. Scan I2C bus to find actual addresses
2. Update corresponding init code
```

## Board Manager Setup (First Time)

If ESP32 boards not showing:

1. **File → Preferences**
2. Find "Additional Boards Manager URLs"
3. Add: `https://dl.espressif.com/dl/package_esp32_index.json`
4. Click OK
5. **Tools → Board → Boards Manager**
6. Search "esp32" → Install "esp32 by Espressif Systems"

## Version Compatibility

```
Arduino IDE: 1.8.13+
ESP32 Board: 3.0.0+
Adafruit_GFX: 1.11.9+
Adafruit_SSD1306: 2.5.10+
Adafruit_AHTX0: 1.2.0+
ScioSense_ENS160: 1.0.0+
ArduinoJson: 7.0.0+
```

## Useful Links

- [Adafruit Libraries GitHub](https://github.com/adafruit)
- [ScioSense Libraries GitHub](https://github.com/sciosense)
- [ArduinoJson Documentation](https://arduinojson.org/)
- [ESP32 Arduino Core](https://github.com/espressif/arduino-esp32)

---

**Last Updated**: April 2024
