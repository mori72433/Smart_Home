/**
 * Smart Home Air Quality Dashboard
 * Real-time sensor data visualization
 */

// ===== CONFIGURATION =====
const API_BASE = window.location.origin;
const REFRESH_INTERVAL_MS = 10000;  // Refresh every 10 seconds
const REQUEST_TIMEOUT_MS = 5000;

// ===== DOM ELEMENTS =====
const tempValue = document.getElementById("tempValue");
const humidityValue = document.getElementById("humidityValue");
const co2Value = document.getElementById("co2Value");
const tvocValue = document.getElementById("tvocValue");
const aqiValue = document.getElementById("aqiValue");
const statusText = document.getElementById("status");
const lastUpdated = document.getElementById("lastUpdated");

// ===== CHART SETUP =====
const trendCtx = document.getElementById("trendChart").getContext("2d");
const trendChart = new Chart(trendCtx, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        label: "Temperature (°C)",
        data: [],
        borderColor: "#d76b2d",
        backgroundColor: "rgba(215, 107, 45, 0.15)",
        tension: 0.35,
        fill: true,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: "#d76b2d",
      },
      {
        label: "Humidity (%)",
        data: [],
        borderColor: "#2a7b6a",
        backgroundColor: "rgba(42, 123, 106, 0.15)",
        tension: 0.35,
        fill: true,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: "#2a7b6a",
      },
      {
        label: "CO2 (ppm)",
        data: [],
        borderColor: "#b8623b",
        backgroundColor: "rgba(184, 98, 59, 0.15)",
        tension: 0.35,
        fill: false,
        borderWidth: 2,
        pointRadius: 2,
        pointBackgroundColor: "#b8623b",
        yAxisID: "y1",
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        position: "top",
        labels: {
          color: "#1b2a2a",
          padding: 15,
          font: {
            size: 12,
            weight: "500",
          },
        },
      },
      filler: {
        propagate: true,
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#5b6c69",
          font: {
            size: 11,
          },
        },
        grid: {
          color: "rgba(91, 108, 105, 0.15)",
          drawBorder: false,
        },
      },
      y: {
        type: "linear",
        display: true,
        position: "left",
        ticks: {
          color: "#5b6c69",
          font: {
            size: 11,
          },
        },
        grid: {
          color: "rgba(91, 108, 105, 0.15)",
          drawBorder: false,
        },
        title: {
          display: true,
          text: "Temp (°C) / Humidity (%)",
          color: "#5b6c69",
        },
      },
      y1: {
        type: "linear",
        display: true,
        position: "right",
        ticks: {
          color: "#b8623b",
          font: {
            size: 11,
          },
        },
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: "CO2 (ppm)",
          color: "#b8623b",
        },
      },
    },
  },
});

// ===== STATE =====
let lastDataTimestamp = null;
let failureCount = 0;
const maxFailures = 3;

// ===== UTILITY FUNCTIONS =====

/**
 * Display status message
 */
function setStatus(text, isError = false) {
  statusText.textContent = text;
  statusText.style.color = isError ? "#d76b2d" : "#2a7b6a";
}

/**
 * Format number to fixed decimal places
 */
function formatNumber(value, digits) {
  if (!Number.isFinite(value)) return "--";
  return value.toFixed(digits);
}

/**
 * Fetch with timeout
 */
async function fetchJson(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
      },
    });

    clearTimeout(timeout);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeout);
    if (error.name === "AbortError") {
      throw new Error("Request timeout");
    }
    throw error;
  }
}

/**
 * Update display with latest sensor values
 */
function updateLatest(data) {
  if (!data) return;

  tempValue.textContent = formatNumber(data.temperature, 1);
  humidityValue.textContent = formatNumber(data.humidity, 1);
  co2Value.textContent = formatNumber(data.co2, 0);
  tvocValue.textContent = formatNumber(data.tvoc, 0);
  
  // Update AQI with color coding
  const aqiLevel = data.aqi ?? 0;
  aqiValue.textContent = aqiLevel;
  
  const aqiColors = ["#2a7b6a", "#b8d44f", "#ffb81c", "#ff6b35", "#e63946", "#8b0000"];
  const aqiLabels = ["Good", "Fair", "Moderate", "Poor", "Very Poor", "Hazardous"];
  aqiValue.style.color = aqiColors[Math.min(aqiLevel, 5)];
  aqiValue.title = aqiLabels[Math.min(aqiLevel, 5)];

  if (data.timestamp) {
    lastUpdated.textContent = new Date(data.timestamp).toLocaleString();
    lastDataTimestamp = new Date(data.timestamp);
  }
}

/**
 * Update chart with sensor data history
 */
function updateChart(readings) {
  if (!readings || readings.length === 0) return;

  const labels = readings.map((item) =>
    new Date(item.timestamp).toLocaleTimeString()
  );

  trendChart.data.labels = labels;
  trendChart.data.datasets[0].data = readings.map((item) => item.temperature);
  trendChart.data.datasets[1].data = readings.map((item) => item.humidity);
  trendChart.data.datasets[2].data = readings.map((item) => item.co2);

  trendChart.update("none");
}

/**
 * Main refresh function - fetches and displays data
 */
async function refreshDashboard() {
  try {
    setStatus("Fetching data...");

    const [latest, readings] = await Promise.all([
      fetchJson("/api/sensor-data/latest"),
      fetchJson("/api/sensor-data?limit=120"),
    ]);

    updateLatest(latest);
    updateChart(readings);
    setStatus("Live");
    failureCount = 0;
  } catch (error) {
    failureCount++;
    console.error("Dashboard refresh error:", error);

    if (failureCount >= maxFailures) {
      setStatus(
        `Connection failed (${failureCount}x) - retrying...`,
        true
      );
    } else {
      setStatus("Connection issue - retrying...", true);
    }

    // Don't update the UI with failed data
  }
}

/**
 * Check API health status
 */
async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// ===== INITIALIZATION =====

async function init() {
  console.log("Initializing Smart Home Dashboard...");
  
  // Check API health
  const isHealthy = await checkHealth();
  if (!isHealthy) {
    setStatus("Waiting for API...", true);
  }

  // Initial refresh
  await refreshDashboard();

  // Set up periodic refresh
  const refreshInterval = setInterval(refreshDashboard, REFRESH_INTERVAL_MS);

  console.log("Dashboard initialized. Refresh interval:", REFRESH_INTERVAL_MS, "ms");
}

// Start dashboard when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
