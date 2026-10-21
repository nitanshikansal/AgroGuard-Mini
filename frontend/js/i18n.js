/**
 * AgroGuard Multilingual Internationalization (i18n) Engine
 * 
 * Provides:
 * - 10 supported Indian regional languages with native names
 * - Instant language switching without page reload
 * - Local storage persistence (restored on page refresh)
 * - DOM scanner for [data-i18n], [data-i18n-placeholder], [data-i18n-title]
 * - Event bus dispatcher ('agroguard:languageChanged') for live telemetry & alerts
 * - Abstracted future Google Cloud Translation API adapter hook
 */

const AGROGUARD_LANGUAGES = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം' }
];

class I18nService {
  constructor() {
    this.storageKey = 'agroguard_language';
    this.currentLanguage = this.loadSavedLanguage();
    this.translations = window.AGROGUARD_TRANSLATIONS || {};
    this.listeners = [];
  }

  loadSavedLanguage() {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (saved && AGROGUARD_LANGUAGES.some(l => l.code === saved)) {
        return saved;
      }
    } catch (e) {
      console.warn('Could not read saved language from localStorage:', e);
    }
    return 'en';
  }

  getCurrentLanguage() {
    return this.currentLanguage;
  }

  getSupportedLanguages() {
    return AGROGUARD_LANGUAGES;
  }

  /**
   * Look up translation key with fallback
   * @param {string} key - e.g. "dash.card_moisture"
   * @param {object} [params] - optional interpolation e.g. { n: 5 }
   * @returns {string}
   */
  t(key, params = null) {
    if (!key) return '';

    const lang = this.currentLanguage;
    let text = this.resolveKey(this.translations[lang], key);

    // Fallback to English if missing in target language
    if (text === undefined && lang !== 'en') {
      text = this.resolveKey(this.translations['en'], key);
    }

    if (text === undefined) {
      return key; // return key if not found
    }

    // Interpolate {param}
    if (params && typeof params === 'object') {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
      }
    }

    return text;
  }

  resolveKey(obj, path) {
    if (!obj || typeof obj !== 'object') return undefined;
    const parts = path.split('.');
    let cur = obj;
    for (const p of parts) {
      if (cur && typeof cur === 'object' && p in cur) {
        cur = cur[p];
      } else {
        return undefined;
      }
    }
    return cur;
  }

  /**
   * Change current language, translate the document, persist, and emit event
   * @param {string} langCode
   */
  async setLanguage(langCode) {
    if (!AGROGUARD_LANGUAGES.some(l => l.code === langCode)) {
      console.warn(`Unsupported language: ${langCode}`);
      return;
    }

    this.currentLanguage = langCode;

    // Save to localStorage
    try {
      localStorage.setItem(this.storageKey, langCode);
    } catch (e) {
      console.warn('Could not save language to localStorage:', e);
    }

    // Update document HTML lang attribute
    document.documentElement.lang = langCode;

    // Translate DOM elements
    this.translateDOM();

    // Update all language selector dropdowns
    this.syncSelectorValues();

    // Dispatch global event for active scripts (dashboard, alerts, auth)
    window.dispatchEvent(new CustomEvent('agroguard:languageChanged', {
      detail: { language: langCode }
    }));

    console.log(`[i18n] Switched language to: ${langCode}`);
  }

  /**
   * Scans and updates all [data-i18n], [data-i18n-placeholder], and [data-i18n-title]
   */
  translateDOM() {
    // 1. Text content
    const textEls = document.querySelectorAll('[data-i18n]');
    textEls.forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (key) {
        const translated = this.t(key);
        // Preserve any nested svg or icon if marked
        if (el.dataset.i18nKeepChildren === 'true') {
          const icon = el.querySelector('svg, img');
          el.textContent = translated;
          if (icon) el.prepend(icon);
        } else {
          el.innerText = translated;
        }
      }
    });

    // 2. Placeholders
    const placeholderEls = document.querySelectorAll('[data-i18n-placeholder]');
    placeholderEls.forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (key) {
        el.placeholder = this.t(key);
      }
    });

    // 3. Titles / tooltips
    const titleEls = document.querySelectorAll('[data-i18n-title]');
    titleEls.forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (key) {
        el.title = this.t(key);
      }
    });

    // 4. Aria Labels
    const ariaEls = document.querySelectorAll('[data-i18n-aria-label]');
    ariaEls.forEach(el => {
      const key = el.getAttribute('data-i18n-aria-label');
      if (key) {
        el.setAttribute('aria-label', this.t(key));
      }
    });

    // 5. Image Alt attributes
    const altEls = document.querySelectorAll('[data-i18n-alt]');
    altEls.forEach(el => {
      const key = el.getAttribute('data-i18n-alt');
      if (key) {
        el.alt = this.t(key);
      }
    });
  }

  syncSelectorValues() {
    const selects = document.querySelectorAll('.lang-select');
    selects.forEach(s => {
      if (s.value !== this.currentLanguage) {
        s.value = this.currentLanguage;
      }
    });
  }

  /**
   * Creates or injects the language selector in the navbar
   */
  initNavbarLanguageSelector() {
    const navMenu = document.getElementById('navMenu');
    if (!navMenu) return;

    // Check if selector already injected
    if (document.getElementById('navLangItem')) return;

    const li = document.createElement('li');
    li.className = 'nav-item nav-lang-item';
    li.id = 'navLangItem';

    const wrapper = document.createElement('div');
    wrapper.className = 'lang-selector-wrapper';

    // Globe SVG icon
    wrapper.innerHTML = `
      <svg class="lang-globe-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="currentColor"/>
      </svg>
      <select class="lang-select" id="navbarLangSelect" aria-label="Select Language">
        ${AGROGUARD_LANGUAGES.map(lang => `
          <option value="${lang.code}" ${lang.code === this.currentLanguage ? 'selected' : ''}>
            ${lang.nativeName} (${lang.name})
          </option>
        `).join('')}
      </select>
    `;

    const selectEl = wrapper.querySelector('select');
    selectEl.addEventListener('change', (e) => {
      this.setLanguage(e.target.value);
    });

    li.appendChild(wrapper);

    // Insert before alerts bell icon or contact
    const bellItem = document.getElementById('navLinkAlerts')?.closest('.nav-item');
    if (bellItem && bellItem.parentNode === navMenu) {
      navMenu.insertBefore(li, bellItem);
    } else {
      navMenu.appendChild(li);
    }
  }

  /* =========================================================
     FUTURE TRANSLATION API INTEGRATION HOOK
     ========================================================= */

  /**
   * Architectural hook for Google Cloud Translation API or custom model endpoint.
   * NOTE: No Google API keys are loaded or exposed client-side.
   * Ready for backend proxy integration (e.g., Flask POST /api/translate).
   */
  async translateDynamicText(text, targetLang) {
    console.log(`[i18n] Future Translation API Hook: "${text}" -> ${targetLang}`);
    // Future backend call:
    // const res = await fetch('/api/translate', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ text, target: targetLang })
    // });
    // const data = await res.json();
    // return data.translatedText;
    return text;
  }
}

// Global Singleton
window.i18n = new I18nService();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.i18n.initNavbarLanguageSelector();
  window.i18n.translateDOM();
});
