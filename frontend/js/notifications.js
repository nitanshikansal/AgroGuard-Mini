/**
 * AgroGuard Farm Alerts & Notification Service
 * 
 * Manages:
 * - Local storage of farm alerts and notifications
 * - Read/unread state, mark-as-read, clear-all, and badge counters
 * - Debounced dynamic alert generation from sensor threshold events
 * - Notification Service Abstraction ready for future Firebase Cloud Messaging (FCM)
 * - Architectural receiver hook for future ESP32-CAM / IoT field event payloads
 */

const NOTIFICATION_CONFIG = {
  STORAGE_KEY: 'agroguard_alerts',
  SETTINGS_KEY: 'agroguard_notification_settings',
  COOLDOWN_SECONDS: 60, // Minimum delay between identical alert types to prevent spamming
  MAX_STORED_ALERTS: 50
};

class NotificationService {
  constructor() {
    this.alerts = this.loadAlerts();
    this.lastTriggerTimes = {}; // In-memory map of { type: timestamp }
    this.subscribers = [];      // UI change listeners

    // Seed initial demo alerts if first time
    if (this.alerts.length === 0) {
      this.seedInitialAlerts();
    }
  }

  /* =========================================================
     PERSISTENCE & STORAGE
     ========================================================= */

  loadAlerts() {
    try {
      const data = localStorage.getItem(NOTIFICATION_CONFIG.STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Failed to parse alerts from storage:', e);
      return [];
    }
  }

  saveAlerts() {
    try {
      localStorage.setItem(NOTIFICATION_CONFIG.STORAGE_KEY, JSON.stringify(this.alerts));
      this.notifySubscribers();
      this.updateNavBadge();
    } catch (e) {
      console.error('Failed to save alerts to storage:', e);
    }
  }

  seedInitialAlerts() {
    const now = Date.now();
    const seeds = [
      {
        id: 'alt_' + (now - 120000),
        type: 'low_moisture',
        title: 'Low Soil Moisture',
        message: 'Soil moisture is low (28%). Irrigation may be required.',
        severity: 'warning',
        timestamp: new Date(now - 120000).toISOString(),
        read: false
      },
      {
        id: 'alt_' + (now - 600000),
        type: 'rain_detected',
        title: 'Rain Detected',
        message: 'Rain detected. Irrigation recommendation has been updated.',
        severity: 'info',
        timestamp: new Date(now - 600000).toISOString(),
        read: false
      },
      {
        id: 'alt_' + (now - 3600000),
        type: 'health_warning',
        title: 'Farm Health Warning',
        message: 'Farm health has decreased. Check current field conditions.',
        severity: 'warning',
        timestamp: new Date(now - 3600000).toISOString(),
        read: true
      },
      {
        id: 'alt_' + (now - 7200000),
        type: 'irrigation_stopped',
        title: 'Irrigation Stopped',
        message: 'Irrigation stopped because the target moisture level was reached.',
        severity: 'info',
        timestamp: new Date(now - 7200000).toISOString(),
        read: true
      }
    ];

    this.alerts = seeds;
    this.saveAlerts();
  }

  /* =========================================================
     READ & QUERY API
     ========================================================= */

  /**
   * Get all alerts ordered newest first
   * @param {string} [filter='all'] - 'all' | 'unread' | 'warning' | 'irrigation'
   * @returns {Array<object>}
   */
  getAlerts(filter = 'all') {
    let list = [...this.alerts].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    if (filter === 'unread') {
      return list.filter(a => !a.read);
    }
    if (filter === 'warning') {
      return list.filter(a => a.severity === 'warning' || a.severity === 'critical');
    }
    if (filter === 'irrigation') {
      return list.filter(a => a.type.startsWith('irrigation_') || a.type === 'low_moisture');
    }
    return list;
  }

  /**
   * Get total number of unread alerts
   * @returns {number}
   */
  getUnreadCount() {
    return this.alerts.filter(a => !a.read).length;
  }

  /* =========================================================
     MUTATION METHODS
     ========================================================= */

  /**
   * Add a new alert to the collection
   * @param {object} param0
   * @param {string} param0.type - Alert category key
   * @param {string} param0.title - Human-friendly title
   * @param {string} param0.message - Descriptive text
   * @param {'info'|'warning'|'critical'|'success'} [param0.severity='info']
   * @returns {object} created alert
   */
  addAlert({ type, title, message, severity = 'info' }) {
    const newAlert = {
      id: 'alt_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
      type,
      title,
      message,
      severity,
      timestamp: new Date().toISOString(),
      read: false
    };

    // Prepend new alert and enforce max storage size
    this.alerts.unshift(newAlert);
    if (this.alerts.length > NOTIFICATION_CONFIG.MAX_STORED_ALERTS) {
      this.alerts = this.alerts.slice(0, NOTIFICATION_CONFIG.MAX_STORED_ALERTS);
    }

    this.saveAlerts();
    return newAlert;
  }

  /**
   * Debounced dynamic trigger from mock sensors or real telemetry
   * Prevents repeated alerts of the same type within cooldown window
   * @param {string} type
   * @param {object} payload - { title, message, severity }
   * @returns {boolean} true if alert was logged, false if throttled
   */
  checkAndTriggerAlert(type, payload) {
    const now = Date.now();
    const lastTrigger = this.lastTriggerTimes[type] || 0;
    const elapsedSeconds = (now - lastTrigger) / 1000;

    if (elapsedSeconds < NOTIFICATION_CONFIG.COOLDOWN_SECONDS) {
      return false; // Suppressed by anti-spam cooldown
    }

    this.lastTriggerTimes[type] = now;
    this.addAlert({
      type,
      title: payload.title,
      message: payload.message,
      severity: payload.severity || 'info'
    });
    return true;
  }

  /**
   * Mark an individual alert as read
   * @param {string} alertId
   */
  markAsRead(alertId) {
    const alert = this.alerts.find(a => a.id === alertId);
    if (alert && !alert.read) {
      alert.read = true;
      this.saveAlerts();
    }
  }

  /**
   * Mark all alerts as read
   */
  markAllAsRead() {
    let changed = false;
    this.alerts.forEach(a => {
      if (!a.read) {
        a.read = true;
        changed = true;
      }
    });
    if (changed) {
      this.saveAlerts();
    }
  }

  /**
   * Delete an individual alert
   * @param {string} alertId
   */
  deleteAlert(alertId) {
    this.alerts = this.alerts.filter(a => a.id !== alertId);
    this.saveAlerts();
  }

  /**
   * Clear all alerts from storage
   */
  clearAll() {
    this.alerts = [];
    this.saveAlerts();
  }

  /* =========================================================
     SUBSCRIPTION & BADGE UPDATES
     ========================================================= */

  subscribe(callback) {
    if (typeof callback === 'function') {
      this.subscribers.push(callback);
    }
  }

  notifySubscribers() {
    this.subscribers.forEach(cb => {
      try { cb(this.alerts); } catch (e) { console.error(e); }
    });
  }

  /**
   * Updates notification bell count badge across all pages
   */
  updateNavBadge() {
    const count = this.getUnreadCount();
    const badges = document.querySelectorAll('.bell-badge');
    badges.forEach(b => {
      if (count > 0) {
        b.innerText = count > 99 ? '99+' : count;
        b.style.display = 'inline-flex';
      } else {
        b.style.display = 'none';
      }
    });
  }

  /**
   * Helper: Format ISO timestamp to relative human time (e.g. "Just now", "5m ago")
   * @param {string} isoString
   * @returns {string}
   */
  getRelativeTime(isoString) {
    const t = (k, fb) => (window.i18n ? window.i18n.t(k) || fb : fb);
    try {
      const date = new Date(isoString);
      const diffMs = Date.now() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      const diffMin = Math.floor(diffSec / 60);
      const diffHour = Math.floor(diffMin / 60);
      const diffDay = Math.floor(diffHour / 24);

      if (diffSec < 30) return t('common.just_now', 'Just now');
      if (diffSec < 60) return `${diffSec}${t('common.seconds_ago', 's ago')}`;
      if (diffMin < 60) return `${diffMin}${t('common.minutes_ago', 'm ago')}`;
      if (diffHour < 24) return `${diffHour}${t('common.hours_ago', 'h ago')}`;
      if (diffDay === 1) return t('common.yesterday', 'Yesterday');
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch (e) {
      return '';
    }
  }

  /**
   * Helper to return translated title and message for an alert
   */
  getLocalizedAlert(alert) {
    if (!window.i18n) return alert;
    const typeKeyTitle = `alert_type.${alert.type}_title`;
    const typeKeyMsg = `alert_type.${alert.type}_msg`;
    const transTitle = window.i18n.t(typeKeyTitle);
    const transMsg = window.i18n.t(typeKeyMsg);

    return {
      ...alert,
      title: (transTitle !== typeKeyTitle) ? transTitle : alert.title,
      message: (transMsg !== typeKeyMsg) ? transMsg : alert.message
    };
  }

  /* =========================================================
     FIREBASE CLOUD MESSAGING (FCM) NOTIFICATION SERVICE HOOKS
     =========================================================
     NOTE: Push notifications are NOT currently active on the client.
     This method outlines where and how FCM integration connects.
     ========================================================= */
  
  /**
   * Placeholder to initialize Firebase Cloud Messaging in the future
   * @param {object} [fcmConfig] - Firebase credentials and VAPID key
   */
  async initFCM(fcmConfig = null) {
    console.log('[NotificationService] FCM Push Service is in mock/local mode.');
    /*
     * TO INTEGRATE FCM PUSH NOTIFICATIONS LATER:
     * 1. Add Firebase Messaging SDK in HTML:
     *    <script src="https://www.gstatic.com/firebasejs/9.x.x/firebase-messaging-compat.js"></script>
     * 2. Place a `firebase-messaging-sw.js` service worker in root.
     * 3. Request user notification permissions:
     *    const perm = await Notification.requestPermission();
     *    if (perm === 'granted') {
     *      const messaging = firebase.messaging();
     *      const token = await messaging.getToken({ vapidKey: fcmConfig.vapidKey });
     *      // Post device token to Flask backend:
     *      await fetch('/api/notifications/register-device', {
     *        method: 'POST',
     *        headers: { 'Content-Type': 'application/json' },
     *        body: JSON.stringify({ token })
     *      });
     *      // Listen for foreground FCM messages:
     *      messaging.onMessage((payload) => {
     *        this.addAlert({
     *          type: payload.data?.type || 'fcm_remote',
     *          title: payload.notification?.title || 'Farm Alert',
     *          message: payload.notification?.body || '',
     *          severity: payload.data?.severity || 'info'
     *        });
     *      });
     *    }
     */
    return { status: 'mock_mode_active' };
  }

  /* =========================================================
     FUTURE IOT GATEWAY: ESP32-CAM INTRUSION ARCHITECTURE HOOK
     =========================================================
     Pipeline Flow:
     [ESP32-CAM Node] → [Flask Backend /api/camera/event] → [NotificationService]
     ========================================================= */

  /**
   * Receiver interface for hardware camera/sensor events from backend
   * @param {object} eventPayload - { deviceId, eventType, timestamp, imageUrl, confidence }
   */
  handleDeviceEvent(eventPayload) {
    console.log('[NotificationService] Processing incoming hardware IoT event:', eventPayload);
    
    // Example future event mapping:
    if (eventPayload.eventType === 'wildlife_intrusion') {
      this.addAlert({
        type: 'intrusion_detected',
        title: 'Boundary Intrusion Alert',
        message: `Camera ${eventPayload.deviceId || 'ESP32-CAM 1'} detected perimeter movement.`,
        severity: 'critical'
      });
    } else {
      this.addAlert({
        type: 'hardware_event',
        title: 'Camera Event',
        message: eventPayload.message || 'New hardware event received from farm node.',
        severity: 'info'
      });
    }
  }
}

// Global notificationService instance
window.notificationService = new NotificationService();

// Auto-initialize badge on DOMContentLoaded if not already done
document.addEventListener('DOMContentLoaded', () => {
  if (window.notificationService) {
    window.notificationService.updateNavBadge();
  }
});
