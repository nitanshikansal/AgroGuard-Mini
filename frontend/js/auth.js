/**
 * AgroGuard Farmer Authentication Service
 * 
 * Modular service supporting:
 * - Mobile Number authentication with OTP verification
 * - Mock OTP mode (default for testing/demo without Firebase credentials)
 * - Firebase Phone Authentication integration ready (switch USE_FIREBASE to true)
 * - Session persistence via localStorage
 * - Farmer profile CRUD operations
 * - Route protection helper for secure pages (dashboard, profile)
 */

const AUTH_CONFIG = {
  // Set to true once you configure Supabase or Firebase SDK
  USE_SUPABASE: false,
  USE_FIREBASE: false,
  
  // Standard demo OTP for offline & development testing
  MOCK_OTP: '123456',
  
  // Simulated network latency in milliseconds
  MOCK_DELAY_MS: 600,
  
  // LocalStorage keys for session & profile persistence
  STORAGE_USER_KEY: 'agroguard_auth_user',
  STORAGE_PROFILE_KEY: 'agroguard_farmer_profile',
  STORAGE_TOKEN_KEY: 'agroguard_auth_token',
  STORAGE_REFRESH_TOKEN_KEY: 'agroguard_refresh_token',
  
  // Expiry time for OTP in seconds
  OTP_EXPIRY_SECONDS: 60,

  // Backend API Base URL (dynamically resolves localhost, 127.0.0.1, or local Wi-Fi IP)
  BACKEND_BASE_URL: (window.AGROGUARD_CONFIG && window.AGROGUARD_CONFIG.API_BASE_URL) ||
    `http://${(typeof window !== 'undefined' && window.location && window.location.hostname) ? window.location.hostname : '127.0.0.1'}:5000`
};

class AuthService {
  constructor() {
    this.pendingPhone = null;
    this.otpTimer = null;
    this.timerSecondsRemaining = 0;
    this.confirmationResult = null; // Used by Firebase Phone Auth
  }

  /* =========================================================
     SESSION & AUTHENTICATION STATE
     ========================================================= */

  /**
   * Check if a farmer is currently authenticated
   * @returns {boolean}
   */
  isAuthenticated() {
    const user = this.getCurrentUser();
    return user !== null && typeof user === 'object' && !!user.phone;
  }

  /**
   * Get the active session user object
   * @returns {object|null}
   */
  getCurrentUser() {
    try {
      const data = localStorage.getItem(AUTH_CONFIG.STORAGE_USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Error reading auth session:', e);
      return null;
    }
  }

  /**
   * Check if the authenticated farmer has finished setting up their farm profile
   * @returns {boolean}
   */
  hasCompletedProfile() {
    const profile = this.getProfile();
    return !!(profile && profile.name && profile.farmName);
  }

  /**
   * Get farmer profile from storage
   * @returns {object|null}
   */
  getProfile() {
    try {
      const data = localStorage.getItem(AUTH_CONFIG.STORAGE_PROFILE_KEY);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Error reading farmer profile:', e);
      return null;
    }
  }

  /**
   * Helper method to perform authenticated backend API requests
   * @param {string} endpoint - e.g. '/farmers'
   * @param {object} [options={}] - Fetch configuration
   * @returns {Promise<any>} Response JSON data
   */
  async apiFetch(endpoint, options = {}) {
    const baseUrl = AUTH_CONFIG.BACKEND_BASE_URL;
    const url = `${baseUrl}${endpoint}`;
    
    const token = this.getAccessToken();
    const headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers
    };

    const response = await fetch(url, config);
    let data = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      try { data = JSON.parse(text); } catch (e) { data = { message: text }; }
    }

    if (!response.ok) {
      const errorMsg = (data && (data.message || data.detail || data.error)) || `HTTP ${response.status} Error`;
      const error = new Error(errorMsg);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  }

  /**
   * Save or update farmer profile and persist to FastAPI backend -> Supabase PostgreSQL
   * @param {object} profileData
   * @returns {Promise<object>} updated profile
   */
  async saveProfile(profileData) {
    const currentUser = this.getCurrentUser();
    const existing = this.getProfile() || {};
    
    const name = (profileData.name || existing.name || '').trim();
    const phone = (profileData.phone || currentUser?.phone || existing.phone || '').trim();
    const farmName = (profileData.farmName || existing.farmName || '').trim();
    const cropName = (profileData.cropName || existing.cropName || '').trim();
    const location = (profileData.location || existing.location || '').trim();
    const farmSize = (profileData.farmSize || existing.farmSize || '').trim();
    const sizeUnit = profileData.sizeUnit || existing.sizeUnit || 'Acres';

    let farmerRecord = null;
    let farmRecord = null;
    const token = this.getAccessToken();

    // Persist to FastAPI -> Supabase PostgreSQL when user fills name & profile credentials
    if (token && name) {
      const formattedPhone = phone ? (phone.startsWith('+91') ? phone : `+91${phone}`) : (currentUser?.phone ? `+91${currentUser.phone}` : '+919876543210');
      
      // A. Create / Update Farmer Profile via POST /farmers
      const farmerPayload = {
        name: name,
        phone: formattedPhone,
        email: profileData.email || existing.email || '',
        preferred_language: (window.i18nService && window.i18nService.currentLang) || existing.preferred_language || 'en',
        region: location
      };

      const farmerRes = await this.apiFetch('/farmers', {
        method: 'POST',
        body: JSON.stringify(farmerPayload)
      });

      farmerRecord = farmerRes.farmer || farmerRes.data || farmerRes;
      console.log('[AGROGUARD] Farmer synced');

      const resolvedFarmerId = farmerRecord.farmer_id || farmerRecord.id;

      // B. Create / Update Farm Plot via POST /farms
      if (farmName) {
        const farmPayload = {
          farmer_id: resolvedFarmerId,
          name: farmName,
          location: location || 'Default Location',
          crop_type: cropName || 'Wheat',
          area_acres: parseFloat(farmSize) || 1.0
        };

        const farmRes = await this.apiFetch('/farms', {
          method: 'POST',
          body: JSON.stringify(farmPayload)
        });

        farmRecord = farmRes.farm || farmRes.data || farmRes;
        console.log('[AGROGUARD] Farm synced');
      }
    }

    // Cache updated profile in localStorage
    const updated = {
      ...existing,
      farmer_id: farmerRecord ? (farmerRecord.farmer_id || farmerRecord.id) : existing.farmer_id,
      farm_id: farmRecord ? (farmRecord.farm_id || farmRecord.id) : existing.farm_id,
      name: name,
      phone: phone,
      farmName: farmName,
      cropName: cropName,
      location: location,
      farmSize: farmSize,
      sizeUnit: sizeUnit,
      updatedAt: new Date().toISOString()
    };

    localStorage.setItem(AUTH_CONFIG.STORAGE_PROFILE_KEY, JSON.stringify(updated));
    return updated;
  }

  /* =========================================================
     MOBILE NUMBER & OTP FLOW
     ========================================================= */

  /**
   * Clean and validate a 10-digit mobile number
   * @param {string} phone
   * @returns {string} cleaned 10-digit phone
   */
  sanitizePhone(phone) {
    if (!phone) return '';
    // Strip everything except digits
    const digits = phone.replace(/\D/g, '');
    // If entered with country code like 919876543210, extract last 10 digits
    if (digits.length > 10 && digits.startsWith('91')) {
      return digits.slice(-10);
    }
    return digits;
  }

  /**
   * Step 1: Send OTP to the farmer's mobile number
   * @param {string} rawPhone
   * @param {string} [appVerifier] - reCAPTCHA verifier for Firebase Phone Auth
   * @returns {Promise<{success: boolean, message: string, mockOtp?: string}>}
   */
  async sendOTP(rawPhone, appVerifier = null) {
    const phone = this.sanitizePhone(rawPhone);

    if (!phone || phone.length !== 10) {
      throw new Error('Please enter a valid 10-digit mobile number.');
    }

    this.pendingPhone = phone;

    // -------------------------------------------------------------
    // OPTION A: SUPABASE PHONE AUTHENTICATION (When enabled)
    // -------------------------------------------------------------
    if (AUTH_CONFIG.USE_SUPABASE || (typeof window.supabase !== 'undefined' && window.supabase && window.supabase.auth)) {
      try {
        const fullInternationalNumber = `+91${phone}`;
        const { data, error } = await window.supabase.auth.signInWithOtp({
          phone: fullInternationalNumber
        });
        if (error) throw error;
        return {
          success: true,
          message: `Verification code sent to +91 ${phone}`,
          data
        };
      } catch (err) {
        console.warn('Supabase Phone Auth notice (falling back if demo mode):', err);
        if (!AUTH_CONFIG.USE_FIREBASE) {
          // fallback to demo mode
        } else {
          throw new Error(err.message || 'Failed to send SMS code via Supabase.');
        }
      }
    }

    // -------------------------------------------------------------
    // OPTION B: FIREBASE PHONE AUTHENTICATION (When enabled)
    // -------------------------------------------------------------
    if (AUTH_CONFIG.USE_FIREBASE) {
      try {
        if (typeof firebase === 'undefined' || !firebase.auth) {
          throw new Error('Firebase SDK not detected. Switch AUTH_CONFIG.USE_FIREBASE to false to use Demo Mock Mode.');
        }
        const fullInternationalNumber = `+91${phone}`;
        this.confirmationResult = await firebase.auth().signInWithPhoneNumber(fullInternationalNumber, appVerifier);
        return {
          success: true,
          message: `Verification code sent to +91 ${phone}`
        };
      } catch (err) {
        console.error('Firebase Phone Auth Error:', err);
        throw new Error(err.message || 'Failed to send SMS code via Firebase.');
      }
    }

    // -------------------------------------------------------------
    // OPTION C: MOCK OTP DEMO MODE (Default for testing without SMS costs)
    // -------------------------------------------------------------
    await new Promise(resolve => setTimeout(resolve, AUTH_CONFIG.MOCK_DELAY_MS));

    return {
      success: true,
      message: `Demo OTP sent to +91 ${phone}`,
      mockOtp: AUTH_CONFIG.MOCK_OTP,
      demoMode: true
    };
  }

  /**
   * Step 2: Verify the 6-digit OTP code entered by the farmer
   * @param {string} enteredOtp
   * @returns {Promise<{success: boolean, user: object, isNewProfile: boolean}>}
   */
  async verifyOTP(enteredOtp) {
    const cleanOtp = (enteredOtp || '').trim();

    if (!cleanOtp || cleanOtp.length !== 6) {
      throw new Error('Please enter the full 6-digit verification code.');
    }

    if (!this.pendingPhone) {
      throw new Error('No mobile number is currently awaiting verification. Please restart login.');
    }

    // SUPABASE VERIFICATION
    if (AUTH_CONFIG.USE_SUPABASE || (typeof window.supabase !== 'undefined' && window.supabase && window.supabase.auth)) {
      try {
        const fullInternationalNumber = `+91${this.pendingPhone}`;
        const { data, error } = await window.supabase.auth.verifyOtp({
          phone: fullInternationalNumber,
          token: cleanOtp,
          type: 'sms'
        });
        if (!error && data && data.session) {
          const sessionUser = {
            uid: data.session.user.id,
            phone: this.pendingPhone,
            fullPhone: fullInternationalNumber,
            loginTime: new Date().toISOString(),
            provider: 'supabase',
            accessToken: data.session.access_token
          };

          localStorage.setItem(AUTH_CONFIG.STORAGE_USER_KEY, JSON.stringify(sessionUser));
          localStorage.setItem(AUTH_CONFIG.STORAGE_TOKEN_KEY, data.session.access_token);
          if (data.session.refresh_token) {
            localStorage.setItem(AUTH_CONFIG.STORAGE_REFRESH_TOKEN_KEY, data.session.refresh_token);
          }

          const existingProfile = this.getProfile();
          const isNew = !existingProfile || !existingProfile.name;
          return { success: true, user: sessionUser, isNewProfile: isNew };
        }
      } catch (err) {
        console.warn('Supabase verifyOtp notice (checking mock fallback):', err);
      }
    }

    // FIREBASE VERIFICATION
    if (AUTH_CONFIG.USE_FIREBASE) {
      if (!this.confirmationResult) {
        throw new Error('No active verification session found. Please request a new code.');
      }
      try {
        const userCredential = await this.confirmationResult.confirm(cleanOtp);
        const firebaseUser = userCredential.user;
        
        const sessionUser = {
          uid: firebaseUser.uid,
          phone: this.pendingPhone,
          fullPhone: `+91${this.pendingPhone}`,
          loginTime: new Date().toISOString()
        };

        localStorage.setItem(AUTH_CONFIG.STORAGE_USER_KEY, JSON.stringify(sessionUser));
        
        const existingProfile = this.getProfile();
        const isNew = !existingProfile || !existingProfile.name;
        
        return { success: true, user: sessionUser, isNewProfile: isNew };
      } catch (err) {
        console.error('Firebase verify error:', err);
        throw new Error('Invalid verification code. Please check and try again.');
      }
    }

    // MOCK VERIFICATION
    await new Promise(resolve => setTimeout(resolve, AUTH_CONFIG.MOCK_DELAY_MS));

    if (cleanOtp !== AUTH_CONFIG.MOCK_OTP) {
      throw new Error(`Invalid code entered. For demo testing, please enter "${AUTH_CONFIG.MOCK_OTP}".`);
    }

    let token = null;
    let authUid = 'demo_farmer_' + this.pendingPhone;

    // Obtain cryptographically signed JWT token from FastAPI backend for development
    try {
      const resp = await fetch(`${AUTH_CONFIG.BACKEND_BASE_URL}/auth/demo-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: `+91${this.pendingPhone}`, auth_user_id: authUid })
      });
      if (resp.ok) {
        const tokenData = await resp.json();
        token = tokenData.access_token;
        if (tokenData.auth_user_id) authUid = tokenData.auth_user_id;
      }
    } catch (e) {
      console.warn('Backend demo-token endpoint unreachable, proceeding with offline mock:', e);
    }

    // Session initialization
    const sessionUser = {
      uid: authUid,
      phone: this.pendingPhone,
      fullPhone: `+91 ${this.pendingPhone}`,
      loginTime: new Date().toISOString(),
      provider: 'mock_demo',
      accessToken: token
    };

    localStorage.setItem(AUTH_CONFIG.STORAGE_USER_KEY, JSON.stringify(sessionUser));
    if (token) {
      localStorage.setItem(AUTH_CONFIG.STORAGE_TOKEN_KEY, token);
    }

    // Check if farmer already has a saved profile matching this phone
    const existingProfile = this.getProfile();
    const isNew = !existingProfile || !existingProfile.name || existingProfile.phone !== this.pendingPhone;

    // If new, seed initial profile with phone number
    if (isNew) {
      this.saveProfile({
        phone: this.pendingPhone,
        name: '',
        farmName: '',
        cropName: '',
        location: '',
        farmSize: ''
      });
    }

    return {
      success: true,
      user: sessionUser,
      isNewProfile: isNew
    };
  }

  /**
   * Get JWT access token for Bearer Authorization headers
   * @returns {string|null}
   */
  getAccessToken() {
    return localStorage.getItem(AUTH_CONFIG.STORAGE_TOKEN_KEY) ||
           (this.getCurrentUser() && this.getCurrentUser().accessToken) ||
           null;
  }

  /**
   * Resend OTP code with safety check
   * @param {string} [appVerifier]
   * @returns {Promise<{success: boolean, message: string, mockOtp?: string}>}
   */
  async resendOTP(appVerifier = null) {
    if (!this.pendingPhone) {
      throw new Error('No pending mobile number found. Please enter your mobile number again.');
    }
    return await this.sendOTP(this.pendingPhone, appVerifier);
  }

  /**
   * Logout the current farmer session
   * @param {string} [redirectUrl='login.html']
   */
  logout(redirectUrl = 'login.html') {
    localStorage.removeItem(AUTH_CONFIG.STORAGE_USER_KEY);
    localStorage.removeItem(AUTH_CONFIG.STORAGE_TOKEN_KEY);
    localStorage.removeItem(AUTH_CONFIG.STORAGE_REFRESH_TOKEN_KEY);
    this.pendingPhone = null;
    this.confirmationResult = null;
    if (typeof window.supabase !== 'undefined' && window.supabase && window.supabase.auth) {
      try { window.supabase.auth.signOut(); } catch (e) {}
    }
    if (redirectUrl) {
      window.location.href = redirectUrl;
    }
  }

  /* =========================================================
     ROUTE PROTECTION (Call on protected pages)
     ========================================================= */

  /**
   * Guard for protected pages. Redirects to login if unauthenticated,
   * or to profile setup if profile is incomplete.
   * @param {string} [returnUrl] - Optional URL to return after authentication
   * @returns {boolean} true if user is authorized to view page
   */
  protectRoute(returnUrl = null) {
    if (!this.isAuthenticated()) {
      const redirect = returnUrl || window.location.pathname.split('/').pop() || 'dashboard.html';
      window.location.replace(`login.html?redirect=${encodeURIComponent(redirect)}`);
      return false;
    }

    if (!this.hasCompletedProfile()) {
      window.location.replace('login.html?step=profile');
      return false;
    }

    return true;
  }
}

// Instantiate global singleton
window.authService = new AuthService();
