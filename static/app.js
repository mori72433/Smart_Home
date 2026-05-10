/**
 * Smart Home Air Quality Dashboard
 * Real-time sensor data visualization
 */

// ===== CONFIGURATION =====
const API_BASE = window.location.origin;
const REFRESH_INTERVAL_MS = 10000;  // Refresh every 10 seconds
const REQUEST_TIMEOUT_MS = 5000;
const DATA_STALE_MS = 45000; // Mark ESP32 offline if no new data within 45s
const TREND_REALTIME_LIMIT = 120;
const TREND_HISTORY_LIMIT = 1000;
const TREND_REALTIME_MINUTES = 1;
const TREND_RANGE_DAYS = {
  week: 7,
  month: 30,
};
const MOTION_LOOKBACK_HOURS = 24;
const MOTION_EVENT_LIMIT = 1000;

// ===== DOM ELEMENTS =====
const tempValue = document.getElementById("tempValue");
const humidityValue = document.getElementById("humidityValue");
const co2Value = document.getElementById("co2Value");
const tvocValue = document.getElementById("tvocValue");
const aqiValue = document.getElementById("aqiValue");
const motionValue = document.getElementById("motionValue");
const motionDetail = document.getElementById("motionDetail");
const motionCard = document.querySelector(".motion-card");
const statusText = document.getElementById("status");
const lastUpdated = document.getElementById("lastUpdated");
const trendRangeLabel = document.getElementById("trendRangeLabel");
const trendButtons = Array.from(document.querySelectorAll(".filter-btn"));

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

const motionCtx = document.getElementById("motionChart").getContext("2d");
const motionChart = new Chart(motionCtx, {
  type: "bar",
  data: {
    labels: [],
    datasets: [
      {
        label: "Motion detections",
        data: [],
        backgroundColor: "rgba(215, 107, 45, 0.35)",
        borderColor: "#d76b2d",
        borderWidth: 1,
        borderRadius: 6,
        maxBarThickness: 28,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          title: (items) => items[0]?.label ?? "",
          label: (item) => `Detections: ${item.parsed.y}`,
        },
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
          color: "rgba(91, 108, 105, 0.12)",
          drawBorder: false,
        },
      },
      y: {
        beginAtZero: true,
        ticks: {
          color: "#5b6c69",
          font: {
            size: 11,
          },
          precision: 0,
          stepSize: 1,
        },
        grid: {
          color: "rgba(91, 108, 105, 0.12)",
          drawBorder: false,
        },
      },
    },
  },
});

// ===== STATE =====
let lastDataTimestamp = null;
let failureCount = 0;
const maxFailures = 3;
let selectedTrendRange = "realtime";

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

function parseApiDate(timestamp) {
  if (!timestamp) return null;
  if (timestamp instanceof Date) return timestamp;
  if (typeof timestamp !== "string") return new Date(timestamp);

  let normalized = timestamp.trim();

  normalized = normalized.replace(/(\.\d{3})\d+/, "$1");
  if (!/Z$|[+-]\d{2}:\d{2}$/.test(normalized)) {
    normalized = `${normalized}Z`;
  }

  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
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
    lastDataTimestamp = parseApiDate(data.timestamp);
    if (lastDataTimestamp) {
      lastUpdated.textContent = lastDataTimestamp.toLocaleString();
    } else {
      lastUpdated.textContent = "--";
    }
  } else {
    lastUpdated.textContent = "--";
  }
}

function isDataFresh() {
  if (!lastDataTimestamp) {
    return false;
  }
  return Date.now() - lastDataTimestamp.getTime() <= DATA_STALE_MS;
}

function clearLatestValues() {
  tempValue.textContent = "--";
  humidityValue.textContent = "--";
  co2Value.textContent = "--";
  tvocValue.textContent = "--";
  aqiValue.textContent = "--";
  aqiValue.style.color = "";
  lastUpdated.textContent = "--";
}

function clearTrendChart() {
  trendChart.data.labels = [];
  trendChart.data.datasets.forEach((dataset) => {
    dataset.data = [];
  });
  trendChart.update("none");
}

function updateDeviceStatus() {
  if (!lastDataTimestamp) {
    setStatus("No data yet", true);
    return;
  }

  if (isDataFresh()) {
    setStatus("ESP32 Live");
  } else {
    setStatus("ESP32 Offline", true);
  }
}

/**
 * Update chart with sensor data history
 */
function updateChart(readings) {
  if (!readings || readings.length === 0) {
    clearTrendChart();
    return;
  }

  const labels = readings.map((item) =>
    (parseApiDate(item.timestamp) ?? new Date(NaN)).toLocaleTimeString()
  );

  trendChart.data.labels = labels;
  trendChart.data.datasets[0].data = readings.map((item) => item.temperature);
  trendChart.data.datasets[1].data = readings.map((item) => item.humidity);
  trendChart.data.datasets[2].data = readings.map((item) => item.co2);

  trendChart.update("none");
}

function getTrendRangeStart(range) {
  if (range === "realtime") {
    const start = new Date();
    start.setMinutes(start.getMinutes() - TREND_REALTIME_MINUTES);
    return start;
  }

  const days = TREND_RANGE_DAYS[range];
  if (!days) {
    return null;
  }

  const start = new Date();
  start.setDate(start.getDate() - days);
  return start;
}

function filterReadingsForRange(readings, range) {
  const start = getTrendRangeStart(range);
  if (!start) {
    return readings;
  }

  return readings.filter((item) => {
    const timestamp = parseApiDate(item.timestamp);
    return timestamp ? timestamp >= start : false;
  });
}

function updateTrendRangeLabel(range, count = null) {
  let labelText = "";
  if (range === "week") {
    labelText = "Last 7 days";
  } else if (range === "month") {
    labelText = "Last 30 days";
  } else {
    labelText = "Last 1 minute";
  }

  if (typeof count === "number") {
    labelText = `${labelText} (${count})`;
  }

  trendRangeLabel.textContent = labelText;
}

function setTrendRange(range) {
  selectedTrendRange = range;
  trendButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.range === range);
  });
  updateTrendRangeLabel(range);
}

function bucketMotionEvents(events, start, end) {
  const labels = [];
  const counts = [];
  let cursor = new Date(start);

  while (cursor < end) {
    labels.push(
      cursor.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    );
    counts.push(0);
    cursor = new Date(cursor.getTime() + 60 * 60 * 1000);
  }

  events.forEach((event) => {
    const timestamp = parseApiDate(event.timestamp);
    if (!timestamp) return;
    const index = Math.floor((timestamp - start) / (60 * 60 * 1000));
    if (index >= 0 && index < counts.length) {
      counts[index] += 1;
    }
  });

  return { labels, counts };
}

function updateMotionPanel(events = []) {
  const end = new Date();
  const start = new Date(end.getTime() - MOTION_LOOKBACK_HOURS * 60 * 60 * 1000);
  const recentEvents = events.filter((event) => {
    const timestamp = parseApiDate(event.timestamp);
    return timestamp ? timestamp >= start && timestamp <= end : false;
  });

  if (recentEvents.length > 0) {
    const lastEvent = recentEvents.reduce((latest, current) => {
      if (!latest) return current;
      const currentTime = parseApiDate(current.timestamp);
      const latestTime = parseApiDate(latest.timestamp);
      if (!currentTime) return latest;
      if (!latestTime) return current;
      return currentTime > latestTime ? current : latest;
    }, null);

    const lastTimestamp = lastEvent ? parseApiDate(lastEvent.timestamp) : null;
    motionValue.textContent = "Detected";
    motionDetail.textContent = lastTimestamp
      ? `Last: ${lastTimestamp.toLocaleString()}`
      : "Last: --";
    motionCard.classList.add("is-active");
  } else {
    motionValue.textContent = "No motion";
    motionDetail.textContent = `No motion in last ${MOTION_LOOKBACK_HOURS} hours`;
    motionCard.classList.remove("is-active");
  }

  const { labels, counts } = bucketMotionEvents(recentEvents, start, end);
  motionChart.data.labels = labels;
  motionChart.data.datasets[0].data = counts;
  motionChart.update("none");
}

function setMotionUnavailable() {
  motionValue.textContent = "--";
  motionDetail.textContent = "Motion data unavailable";
  motionCard.classList.remove("is-active");
  motionChart.data.labels = [];
  motionChart.data.datasets[0].data = [];
  motionChart.update("none");
}

function setMotionOffline() {
  motionValue.textContent = "Offline";
  motionDetail.textContent = "ESP32 offline";
  motionCard.classList.remove("is-active");
}

/**
 * Main refresh function - fetches and displays data
 */
async function refreshDashboard() {
  try {
    setStatus("Fetching data...");

    const readingsLimit =
      selectedTrendRange === "realtime" ? TREND_REALTIME_LIMIT : TREND_HISTORY_LIMIT;

    const [latest, readings] = await Promise.all([
      fetchJson("/api/sensor-data/latest"),
      fetchJson(`/api/sensor-data?limit=${readingsLimit}`),
    ]);

    updateLatest(latest);
    const filteredReadings = filterReadingsForRange(readings, selectedTrendRange);
    updateChart(filteredReadings);
    updateTrendRangeLabel(selectedTrendRange, filteredReadings.length);
    if (!isDataFresh()) {
      clearLatestValues();
      setMotionOffline();
    }
    updateDeviceStatus();
    failureCount = 0;
  } catch (error) {
    failureCount++;
    console.error("Dashboard refresh error:", error);

    clearLatestValues();
    setMotionOffline();
    setStatus("ESP32 Offline", true);
    return;
  }

  if (!isDataFresh()) {
    setMotionOffline();
    return;
  }

  try {
    const motionEvents = await fetchJson(
      `/api/motion-events?hours=${MOTION_LOOKBACK_HOURS}&limit=${MOTION_EVENT_LIMIT}`
    );
    updateMotionPanel(motionEvents);
  } catch (error) {
    console.warn("Motion data fetch error:", error);
    setMotionUnavailable();
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

  trendButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const range = button.dataset.range;
      if (!range || range === selectedTrendRange) {
        return;
      }
      setTrendRange(range);
      refreshDashboard();
    });
  });

  setTrendRange(selectedTrendRange);
  
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
