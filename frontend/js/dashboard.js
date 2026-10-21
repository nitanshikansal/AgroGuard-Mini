/**
 * AgroGuard Dashboard Script — Flask REST Integration
 * ====================================================
 * Connects frontend telemetry console with the AgroGuard Flask backend API (http://127.0.0.1:5000).
 * Consumes:
 *   - GET /sensor
 *   - GET /weather
 *   - GET /dashboard
 *   - GET /farm-health  (AFHI backend source of truth — no frontend recalculation)
 *   - GET /recommendation (CAII & SPAE backend source of truth)
 *   - GET /control/pump
 *   - POST /control/pump
 *
 * Preserves complete backward compatibility, multilingual support (10 Indian languages),
 * route security, and dynamic farmer alert triggers.
 */

// ==========================================
// 1. CONFIGURATION & CENTRALIZED API BASE URL
// ==========================================
const CONFIG = {
  // Set to false for live Flask integration; true for offline mock fallback
  MOCK_API: false,
  // Centralized backend API base URL (dynamically resolves localhost, 127.0.0.1, or local Wi-Fi IP)
  BACKEND_BASE_URL: (window.AGROGUARD_CONFIG && window.AGROGUARD_CONFIG.API_BASE_URL) ||
    `http://${(typeof window !== 'undefined' && window.location && window.location.hostname) ? window.location.hostname : '127.0.0.1'}:5000`,
  // Polling cadence for live telemetry sync
  POLL_INTERVAL_MS: 5000
};

// Global Dashboard State
const dashboardState = {
  telemetry: {
    temperature: 27.4,
    humidity: 62.0,
    soil_moisture: 45.0,
    rain_status: "No Rain",
    water_level: 78.0,
    timestamp: new Date().toISOString()
  },
  weather: {
    temp: 28,
    condition: "Partly Cloudy",
    high: 31,
    low: 22
  },
  farmHealth: {
    score: 85,
    status: "Excellent",
    color: "#16a34a",
    components: {
      soil_moisture: 100.0,
      temperature: 100.0,
      humidity: 100.0,
      rain: 95.0,
      water_level: 100.0
    },
    methodology: "Rule-based weighted multi-criteria decision-support methodology"
  },
  recommendation: {
    crop: "Maize (Corn)",
    irrigation: "Sufficient moisture. Watering not required.",
    caii: {
      state: "Moisture Adequate",
      action: "none",
      message: "Soil moisture is optimal. No watering required.",
      pump_active: false
    },
    spae: {
      state: "Suitable",
      action: "proceed_with_care",
      message: "Weather and ambient conditions are favorable for spraying. Follow PPE protocols.",
      factors: {
        rain_detected: false,
        humidity_high: false,
        temperature_extreme: false
      }
    },
    alerts_ready: []
  },
  lastUpdated: new Date(),
  isPumpActive: false,
  isAutoIrrigation: true,
  // Moisture history for sparkline (last 10 readings)
  moistureHistory: [40, 42, 41, 43, 44, 46, 45, 44, 45, 45]
};

// ==========================================
// 2. FLASK API SERVICE LAYER
// ==========================================
class AgroGuardDataService {
  /**
   * Helper method for performing JSON fetch with timeout & CORS safety
   */
  async _fetch(endpoint, options = {}) {
    const url = `${CONFIG.BACKEND_BASE_URL}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const headers = {
      'Accept': 'application/json',
      ...(options.headers || {})
    };

    // Inject Bearer JWT token from auth service if available
    const token = (window.authService && typeof window.authService.getAccessToken === 'function')
      ? window.authService.getAccessToken()
      : localStorage.getItem('agroguard_auth_token');

    if (token && !headers['Authorization'] && !headers['authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: headers
      });
      clearTimeout(timeoutId);

      if (response.status === 401) {
        console.warn(`[AgroGuard] Authentication required for ${endpoint}. Redirecting to login.`);
        if (window.location.pathname.indexOf('login.html') === -1) {
          window.location.replace('login.html?session_expired=true');
        }
        throw new Error(`Authentication required (401) from ${endpoint}`);
      }

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status} from ${endpoint}`);
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }

  /**
   * Fetches latest sensor readings.
   * Matches Flask API: GET /sensor
   */
  async fetchSensorData() {
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 150));
      return { ...dashboardState.telemetry };
    }
    return await this._fetch('/sensor');
  }

  /**
   * Fetches latest weather forecast.
   * Matches Flask API: GET /weather
   */
  async fetchWeatherData() {
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 150));
      return { ...dashboardState.weather };
    }
    return await this._fetch('/weather');
  }

  /**
   * Fetches comprehensive overall dashboard summary.
   * Matches Flask API: GET /dashboard
   */
  async fetchDashboardSummary() {
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 200));
      return {
        telemetry: dashboardState.telemetry,
        weather: dashboardState.weather,
        farmHealth: dashboardState.farmHealth,
        recommendation: dashboardState.recommendation,
        pump: {
          active: dashboardState.isPumpActive,
          status: dashboardState.isPumpActive ? 'running' : 'stopped',
          mode: 'manual'
        }
      };
    }
    return await this._fetch('/dashboard');
  }

  /**
   * Fetches AFHI farm health index.
   * Matches Flask API: GET /farm-health
   */
  async fetchFarmHealth() {
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 150));
      return { ...dashboardState.farmHealth };
    }
    return await this._fetch('/farm-health');
  }

  /**
   * Fetches crop, CAII irrigation, and SPAE pesticide recommendations.
   * Matches Flask API: GET /recommendation
   */
  async fetchRecommendation() {
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 150));
      return { ...dashboardState.recommendation };
    }
    return await this._fetch('/recommendation');
  }

  /**
   * Fetches current actuator state.
   * Matches Flask API: GET /control/pump
   */
  async fetchPumpStatus() {
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 100));
      return {
        active: dashboardState.isPumpActive,
        status: dashboardState.isPumpActive ? 'running' : 'stopped',
        mode: 'manual'
      };
    }
    return await this._fetch('/control/pump');
  }

  /**
   * Sets pump state via POST, then queries GET /control/pump to confirm.
   * Matches Flask API: POST /control/pump -> GET /control/pump
   */
  async togglePump(state) {
    console.log(`Sending command to Flask controller: Pump active = ${state}`);
    if (CONFIG.MOCK_API) {
      await new Promise(resolve => setTimeout(resolve, 200));
      dashboardState.isPumpActive = state;
      return { success: true, active: state, status: state ? 'running' : 'stopped' };
    }

    // 1. Send POST /control/pump
    const postResult = await this._fetch('/control/pump', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: Boolean(state) })
    });

    // 2. Query GET /control/pump to verify the confirmed actuator state
    try {
      const verifiedPump = await this.fetchPumpStatus();
      return {
        ...postResult,
        pump: verifiedPump,
        active: verifiedPump.active,
        status: verifiedPump.status
      };
    } catch (e) {
      return postResult;
    }
  }
}

const dataService = new AgroGuardDataService();

// ==========================================
// 3. DASHBOARD UI CONTROLLER & LIFECYCLE
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  // Initialize farmer details from profile
  initFarmerHeader();

  // Setup user interaction listeners
  setupEventListeners();

  // Initial draw of sparkline
  drawChart();

  // Initial dashboard load from Flask backend
  refreshDashboard();

  // Periodic polling synchronization
  setInterval(() => {
    if (!CONFIG.MOCK_API) {
      refreshDashboard();
    } else {
      simulateLiveFluctuations();
    }
  }, CONFIG.POLL_INTERVAL_MS);
});

function initFarmerHeader() {
  if (typeof authService !== 'undefined') {
    const profile = authService.getProfile();
    const farmerEl = document.getElementById('dashFarmerName');
    const farmEl = document.getElementById('dashFarmName');
    if (farmerEl && profile?.name) farmerEl.innerText = profile.name;
    if (farmEl && profile?.farmName) farmEl.innerText = profile.farmName;
  }
}

function setupEventListeners() {
  const btnRefresh = document.getElementById('btnRefresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', refreshDashboard);
  }

  const btnRetrySync = document.getElementById('btnRetrySync');
  if (btnRetrySync) {
    btnRetrySync.addEventListener('click', refreshDashboard);
  }

  const btnPump = document.getElementById('btnPump');
  if (btnPump) {
    btnPump.addEventListener('click', toggleManualPump);
  }

  const btnDashboardLogout = document.getElementById('btnDashboardLogout');
  if (btnDashboardLogout) {
    btnDashboardLogout.addEventListener('click', () => {
      const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
      if (confirm(t('common.confirm_logout', 'Are you sure you want to log out of AgroGuard?'))) {
        authService.logout('login.html');
      }
    });
  }

  const switchAuto = document.getElementById('switchAuto');
  if (switchAuto) {
    switchAuto.addEventListener('change', (e) => {
      dashboardState.isAutoIrrigation = e.target.checked;
      updateUI();
    });
  }
}

// ==========================================
// 4. SYNCHRONIZATION & ERROR/LOADING HANDLING
// ==========================================
/**
 * Synchronizes dashboard state from the Flask backend.
 * Uses /dashboard endpoint as unified source of truth.
 */
async function refreshDashboard() {
  const btnRefresh = document.getElementById('btnRefresh');
  if (btnRefresh) btnRefresh.classList.add('loading');

  try {
    const summary = await dataService.fetchDashboardSummary();

    // 1. Telemetry State
    if (summary.telemetry) {
      dashboardState.telemetry = { ...summary.telemetry };

      // Sparkline history update
      if (typeof summary.telemetry.soil_moisture === 'number') {
        dashboardState.moistureHistory.push(parseFloat(summary.telemetry.soil_moisture.toFixed(1)));
        if (dashboardState.moistureHistory.length > 10) {
          dashboardState.moistureHistory.shift();
        }
        drawChart();
      }

      // Backend timestamp extraction
      if (summary.telemetry.timestamp) {
        try {
          const d = new Date(summary.telemetry.timestamp);
          if (!isNaN(d.getTime())) dashboardState.lastUpdated = d;
        } catch (e) {
          dashboardState.lastUpdated = new Date();
        }
      }
    }

    // 2. Weather State
    if (summary.weather) {
      dashboardState.weather = { ...summary.weather };
    }

    // 3. AFHI Farm Health Index (Backend is source of truth — no recalculation)
    if (summary.farmHealth) {
      dashboardState.farmHealth = { ...summary.farmHealth };
    }

    // 4. CAII Irrigation & SPAE Pesticide Recommendations
    if (summary.recommendation) {
      dashboardState.recommendation = { ...summary.recommendation };
    }

    // 5. Pump Actuator State
    if (summary.pump && typeof summary.pump.active === 'boolean') {
      dashboardState.isPumpActive = summary.pump.active;
    }

    // Clear error states on success
    clearFarmError();

    // Check alert trigger candidates for dynamic notification badge
    checkSensorAlerts(dashboardState.telemetry, dashboardState.farmHealth, dashboardState.recommendation);

    // Update DOM elements
    updateUI();
  } catch (error) {
    console.warn('Unable to sync metrics with farm controller:', error);
    showFarmError();
  } finally {
    if (btnRefresh) {
      setTimeout(() => btnRefresh.classList.remove('loading'), 400);
    }
  }
}

/**
 * Displays a farmer-friendly error notice without raw JS exceptions
 */
function showFarmError(customMsg) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  const errorBanner = document.getElementById('dashErrorBanner');
  const errorText = document.getElementById('dashErrorText');
  const liveDot = document.getElementById('liveStatusDot');
  const liveText = document.getElementById('liveStatusText');

  const msg = customMsg || t('dash.error_connection', 'Unable to connect to the farm controller. Please check the connection.');

  if (errorBanner) {
    if (errorText) errorText.innerText = msg;
    errorBanner.style.display = 'flex';
  }

  if (liveDot) {
    liveDot.className = 'status-indicator offline';
  }
  if (liveText) {
    liveText.innerText = t('common.status_offline', 'Controller Offline');
    liveText.style.color = 'var(--color-danger, #ef4444)';
  }
}

/**
 * Restores live green status when backend connectivity is healthy
 */
function clearFarmError() {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  const errorBanner = document.getElementById('dashErrorBanner');
  const liveDot = document.getElementById('liveStatusDot');
  const liveText = document.getElementById('liveStatusText');

  if (errorBanner) {
    errorBanner.style.display = 'none';
  }
  if (liveDot) {
    liveDot.className = 'status-indicator live';
  }
  if (liveText) {
    liveText.innerText = t('common.status_live', 'Microcontroller Live');
    liveText.style.color = 'var(--primary-green)';
  }
}

// ==========================================
// 5. PUMP ACTUATOR CONTROL
// ==========================================
/**
 * Toggles the state of the water pump manual override
 */
async function toggleManualPump() {
  const btnPump = document.getElementById('btnPump');
  if (!btnPump) return;

  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  const targetState = !dashboardState.isPumpActive;
  btnPump.disabled = true;
  btnPump.innerText = targetState ? t('dash.pump_turning_on', "Turning On...") : t('dash.pump_turning_off', "Turning Off...");

  try {
    const response = await dataService.togglePump(targetState);
    const confirmedActive = (response.pump && typeof response.pump.active === 'boolean')
      ? response.pump.active
      : (typeof response.active === 'boolean' ? response.active : targetState);

    dashboardState.isPumpActive = confirmedActive;
    updatePumpUI();

    // Trigger farmer notifications
    if (typeof notificationService !== 'undefined') {
      if (confirmedActive) {
        notificationService.checkAndTriggerAlert('irrigation_started', {
          title: t('alert_type.irrigation_started_title', 'Irrigation Started'),
          message: t('alert_type.irrigation_started_msg', 'Automatic irrigation has started.'),
          severity: 'success'
        });
      } else {
        notificationService.checkAndTriggerAlert('irrigation_stopped', {
          title: t('alert_type.irrigation_stopped_title', 'Irrigation Stopped'),
          message: t('alert_type.irrigation_stopped_manual', 'Irrigation stopped by farmer override.'),
          severity: 'info'
        });
      }
    }

    // Refresh immediately to capture updated telemetry & CAII state
    await refreshDashboard();
  } catch (error) {
    console.error('Failed to command pump microcontroller:', error);
    showFarmError(t('dash.pump_error', 'Unable to command water pump. Please verify connection.'));
  } finally {
    btnPump.disabled = false;
  }
}

function updatePumpUI() {
  const btnPump = document.getElementById('btnPump');
  if (!btnPump) return;
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);

  if (dashboardState.isPumpActive) {
    btnPump.classList.add('active');
    btnPump.innerHTML = `
      <svg style="width:16px;height:16px;margin-right:8px;animation:spin 2s infinite linear;" viewBox="0 0 24 24"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2.5V2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6V11.5L16.25,14L17,12.75L13.5,10.68V6H12Z" fill="currentColor"/></svg>
      ${t('dash.pump_active', 'Pump Active (Stop)')}
    `;
  } else {
    btnPump.classList.remove('active');
    btnPump.innerHTML = `
      <svg style="width:16px;height:16px;margin-right:8px;" viewBox="0 0 24 24"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6V11.5L16.25,14L17,12.75L13.5,10.68V6H12Z" fill="currentColor"/></svg>
      ${t('dash.pump_test', 'Test Irrigation Pump')}
    `;
  }
}

// ==========================================
// 6. DOM RENDERING & STATUS LOCALIZATION
// ==========================================
function updateUI() {
  const t = dashboardState.telemetry;

  // 1. Sensor Values
  updateMetricValue('tempVal', `${Number(t.temperature).toFixed(1)} °C`);
  updateMetricValue('humidityVal', `${Number(t.humidity).toFixed(0)} %`);
  updateMetricValue('moistureVal', `${Number(t.soil_moisture).toFixed(0)} %`);
  updateMetricValue('waterVal', `${Number(t.water_level).toFixed(0)} %`);
  updateMetricValue('rainVal', getRainStatus(t.rain_status).text);

  // 2. Status Indicators
  updateStatusStyle('moistureStatus', getMoistureStatus(t.soil_moisture));
  updateStatusStyle('tempStatus', getTempStatus(t.temperature));
  updateStatusStyle('waterStatus', getWaterStatus(t.water_level));
  updateStatusStyle('rainStatus', getRainStatus(t.rain_status));

  // 3. Farm Health Progress Ring (AFHI Backend Value)
  const healthScore = dashboardState.farmHealth.score || 0;
  const healthLabel = dashboardState.farmHealth.status || 'Good';
  updateMetricValue('healthVal', translateAFHIStatus(healthLabel));

  const circle = document.getElementById('healthCircle');
  const textScore = document.getElementById('healthScoreText');
  if (circle && textScore) {
    const circumference = 226;
    const offset = circumference - (Math.min(100, Math.max(0, healthScore)) / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    textScore.innerText = `${Math.round(healthScore)}%`;

    // Dynamic stroke color from backend or score scale
    if (dashboardState.farmHealth.color) {
      circle.style.stroke = dashboardState.farmHealth.color;
    } else if (healthScore >= 80) {
      circle.style.stroke = 'var(--primary-green)';
    } else if (healthScore >= 50) {
      circle.style.stroke = 'var(--color-warning)';
    } else {
      circle.style.stroke = 'var(--color-danger)';
    }
  }

  // 4. Recommendations (CAII & SPAE)
  const rec = dashboardState.recommendation;
  updateMetricValue('recCrop', rec.crop || 'Maize (Corn)');
  updateMetricValue('recText', rec.irrigation || 'Sufficient moisture. Watering not required.');

  // SPAE Pesticide Advisory Display
  if (rec.spae) {
    const spaeBadge = document.getElementById('spaeStatusBadge');
    const spaeText = document.getElementById('spaeText');
    const spaeState = rec.spae.state || 'Suitable';

    if (spaeBadge) {
      let badgeClass = 'normal';
      if (spaeState === 'Caution') badgeClass = 'warning';
      if (spaeState === 'Unsafe') badgeClass = 'danger';
      spaeBadge.className = `dashboard-card-status ${badgeClass}`;
      spaeBadge.innerText = translateSPAEState(spaeState);
    }

    if (spaeText) {
      spaeText.innerText = rec.spae.message || 'Environmental conditions are favorable.';
    }
  }

  // 5. Weather Forecast Card
  const w = dashboardState.weather;
  updateMetricValue('weatherTemp', `${Math.round(w.temp)}°C`);
  updateMetricValue('weatherCondition', w.condition || 'Partly Cloudy');
  updateMetricValue('weatherRange', `H: ${Math.round(w.high)}° | L: ${Math.round(w.low)}°`);

  // 6. Pump Control Button
  updatePumpUI();

  // 7. Last Updated Timestamp
  const ts = document.getElementById('timestamp');
  if (ts) {
    ts.innerText = dashboardState.lastUpdated.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }
}

function updateMetricValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerText = value;
}

function updateStatusStyle(id, statusObj) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `dashboard-card-status ${statusObj.class}`;
  el.innerText = statusObj.text;
}

function translateAFHIStatus(status) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  const map = {
    'Excellent': t('status.excellent', 'Excellent'),
    'Good': t('status.good', 'Good'),
    'Needs Attention': t('status.needs_attention', 'Needs Attention'),
    'Critical': t('status.critical', 'Critical')
  };
  return map[status] || status || '--';
}

function translateSPAEState(state) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  const map = {
    'Suitable': t('spae.state_suitable', 'Suitable'),
    'Caution': t('spae.state_caution', 'Caution'),
    'Unsafe': t('spae.state_unsafe', 'Unsafe')
  };
  return map[state] || state || '--';
}

function getMoistureStatus(val) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  if (val < 25) return { text: t('status.critical_dry', "Critical Dry"), class: "danger" };
  if (val < 40) return { text: t('status.needs_watering', "Needs Watering"), class: "warning" };
  if (val <= 75) return { text: t('status.optimal', "Optimal"), class: "normal" };
  return { text: t('status.wet', "Wet / Saturated"), class: "info" };
}

function getTempStatus(val) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  if (val < 15) return { text: t('status.cool', "Cool"), class: "info" };
  if (val <= 32) return { text: t('status.optimal', "Optimal"), class: "normal" };
  return { text: t('status.high_temp', "High Temperature"), class: "warning" };
}

function getWaterStatus(val) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  if (val < 20) return { text: t('status.low_supply', "Low Supply"), class: "danger" };
  if (val < 60) return { text: t('status.adequate', "Adequate"), class: "warning" };
  return { text: t('status.sufficient', "Sufficient"), class: "normal" };
}

function getRainStatus(status) {
  const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
  if (status === false || status === "No Rain" || !status) {
    return { text: t('status.no_rain', "No Rain"), class: "normal" };
  }
  if (status === "Light Rain") {
    return { text: t('status.light_rain', "Light Rain"), class: "info" };
  }
  return { text: t('status.heavy_storm', "Heavy Storm"), class: "warning" };
}

// ==========================================
// 7. ALERT TRIGGERING BRIDGE
// ==========================================
function checkSensorAlerts(t, farmHealth, rec) {
  if (typeof notificationService === 'undefined') return;
  const translate = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);

  // 1. Low soil moisture
  if (t.soil_moisture < 25) {
    notificationService.checkAndTriggerAlert('low_moisture', {
      title: translate('alert_type.low_moisture_title', 'Low Soil Moisture'),
      message: translate('alert_type.low_moisture_msg', 'Soil moisture is low. Irrigation may be required.'),
      severity: 'critical'
    });
  }

  // 2. Rain detected
  const isRaining = t.rain_status && t.rain_status !== 'No Rain' && t.rain_status !== false;
  if (isRaining) {
    notificationService.checkAndTriggerAlert('rain_detected', {
      title: translate('alert_type.rain_detected_title', 'Rain Detected'),
      message: translate('alert_type.rain_detected_msg', 'Rain detected. Irrigation recommendation has been updated.'),
      severity: 'info'
    });
  }

  // 3. Low water level
  if (t.water_level < 20) {
    notificationService.checkAndTriggerAlert('low_water', {
      title: translate('alert_type.low_water_title', 'Low Water Level'),
      message: translate('alert_type.low_water_msg', 'Farm water availability is low.'),
      severity: 'critical'
    });
  }

  // 4. Farm health warning
  if (farmHealth && farmHealth.score < 60) {
    notificationService.checkAndTriggerAlert('health_warning', {
      title: translate('alert_type.health_warning_title', 'Farm Health Warning'),
      message: translate('alert_type.health_warning_msg', 'Farm health has decreased. Check current field conditions.'),
      severity: 'warning'
    });
  }

  // 5. Consume backend alerts_ready if provided
  if (rec && Array.isArray(rec.alerts_ready)) {
    for (const alert of rec.alerts_ready) {
      notificationService.checkAndTriggerAlert(alert.type, {
        title: alert.title,
        message: alert.message,
        severity: alert.severity || 'warning'
      });
    }
  }
}

// ==========================================
// 8. DYNAMIC SVG SPARKLINE
// ==========================================
function drawChart() {
  const chartPath = document.getElementById('chartLine');
  const chartArea = document.getElementById('chartArea');
  if (!chartPath || !chartArea) return;

  const data = dashboardState.moistureHistory;
  const width = 600;
  const height = 100;

  const minVal = Math.min(...data) - 2;
  const maxVal = Math.max(...data) + 2;
  const range = maxVal - minVal || 1;

  const points = data.map((val, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((val - minVal) / range) * (height - 10) - 5;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const dAttribute = `M ${points.join(' L ')}`;
  chartPath.setAttribute('d', dAttribute);

  const areaAttribute = `${dAttribute} L ${width},${height} L 0,${height} Z`;
  chartArea.setAttribute('d', areaAttribute);
}

// ==========================================
// 9. OFFLINE MOCK SIMULATION FALLBACK
// ==========================================
function simulateLiveFluctuations() {
  const t = dashboardState.telemetry;
  if (dashboardState.isPumpActive) {
    t.soil_moisture = Math.min(85, t.soil_moisture + 3.5);
    t.water_level = Math.max(10, t.water_level - 1.2);
  } else {
    t.soil_moisture = Math.max(15, t.soil_moisture - 0.2);
  }
  dashboardState.lastUpdated = new Date();
  updateUI();
}

// ==========================================
// 10. MULTILINGUAL RE-RENDER EVENT
// ==========================================
window.addEventListener('agroguard:languageChanged', () => {
  updateUI();
});
