/**
 * AgroGuard Shared Frontend Scripts
 * Manages sticky navbar, hamburger mobile menu, scroll reveal animations,
 * active page highlights, and form validations.
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initMobileMenu();
  initScrollAnimations();
  highlightActivePage();
  initContactForm();
  initNavAuthState();
  if (window.notificationService) {
    window.notificationService.updateNavBadge();
  }
});

/**
 * Adds backdrop-filter styling to the navbar when the page is scrolled
 */
function initNavbar() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  const handleScroll = () => {
    if (window.scrollY > 20) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };

  // Run on load and scroll
  handleScroll();
  window.addEventListener('scroll', handleScroll);
}

/**
 * Manages the mobile burger menu slider layout and overlay toggle
 */
function initMobileMenu() {
  const hamburger = document.querySelector('.hamburger');
  const navMenu = document.querySelector('.nav-menu');

  if (!hamburger || !navMenu) return;

  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navMenu.classList.toggle('active');
  });

  // Close menu when clicking navigation links
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      hamburger.classList.remove('active');
      navMenu.classList.remove('active');
    });
  });

  // Close menu when clicking outside
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
      hamburger.classList.remove('active');
      navMenu.classList.remove('active');
    }
  });
}

/**
 * Uses IntersectionObserver to trigger slick fade-in slide-up animation entry elements
 */
function initScrollAnimations() {
  const revealElements = document.querySelectorAll('.reveal');
  
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
          // Once animated, we don't need to track it anymore
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
  } else {
    // Fallback if browser doesn't support IntersectionObserver
    revealElements.forEach(el => el.classList.add('active'));
  }
}

/**
 * Dynamically highlights active navigation links matching current path
 */
function highlightActivePage() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');

  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    
    // Exact match or matches index if path is empty/root
    if (currentPath.endsWith(href) || 
        (href === 'index.html' && (currentPath.endsWith('/') || currentPath === ''))) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

/**
 * Performs client-side validation and displays a modern toast/feedback banner on submission
 */
function initContactForm() {
  const form = document.getElementById('contactForm');
  const feedback = document.getElementById('formFeedback');

  if (!form || !feedback) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    // Fetch values
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const message = document.getElementById('message').value.trim();

    if (!name || !email || !subject || !message) {
      showFeedback(window.i18n ? window.i18n.t('contact.fill_fields') : 'Please fill out all required fields.', 'error');
      return;
    }

    // Basic email regex validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showFeedback(window.i18n ? window.i18n.t('contact.invalid_email') : 'Please enter a valid email address.', 'error');
      return;
    }

    // Simulate sending message to Flask (mock AJAX response)
    const btn = form.querySelector('.btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = window.i18n ? window.i18n.t('contact.sending') : 'Sending Message...';

    setTimeout(() => {
      btn.innerHTML = window.i18n ? window.i18n.t('contact.sent') : 'Message Sent!';
      const thankMsg = window.i18n ? window.i18n.t('contact.thank_you', { name }) : ('Thank you, ' + name + '! Your message has been sent successfully. The AgroGuard team will respond shortly.');
      showFeedback(thankMsg, 'success');
      form.reset();

      // Reset labels floating state
      const inputs = form.querySelectorAll('.form-control');
      inputs.forEach(input => {
        // Triggers change listener
        input.dispatchEvent(new Event('input', { bubbles: true }));
      });

      // Restore button status after a delay
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;
      }, 3000);
    }, 1500);
  });

  function showFeedback(text, type) {
    feedback.innerText = text;
    feedback.style.display = 'block';
    
    if (type === 'error') {
      feedback.style.backgroundColor = 'hsl(4, 90%, 96%)';
      feedback.style.color = 'var(--color-danger)';
      feedback.style.borderColor = 'rgba(239, 68, 68, 0.2)';
    } else {
      feedback.style.backgroundColor = 'var(--primary-green-light)';
      feedback.style.color = 'var(--primary-green)';
      feedback.style.borderColor = 'rgba(21, 128, 61, 0.2)';
    }
  }
}

/**
 * Dynamically updates navbar actions based on farmer authentication state
 */
function initNavAuthState() {
  if (typeof authService === 'undefined') return;

  const navMenu = document.getElementById('navMenu');
  if (!navMenu) return;

  const isAuth = authService.isAuthenticated();

  // Create or update auth action list item
  let authActionItem = document.getElementById('navAuthItem');
  if (!authActionItem) {
    authActionItem = document.createElement('li');
    authActionItem.className = 'nav-item';
    authActionItem.id = 'navAuthItem';
    navMenu.appendChild(authActionItem);
  }

  const logoutText = window.i18n ? window.i18n.t('nav.logout') : 'Logout';
  const loginText = window.i18n ? window.i18n.t('nav.farmer_login') : 'Farmer Login';

  if (isAuth) {
    authActionItem.innerHTML = `
      <a href="login.html" id="navLogoutLink" class="nav-link" style="color: var(--color-danger); font-weight: 600;" data-i18n="nav.logout">
        ${logoutText}
      </a>
    `;
    const logoutBtn = document.getElementById('navLogoutLink');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const confirmMsg = window.i18n ? window.i18n.t('auth.confirm_logout') : 'Are you sure you want to log out of AgroGuard?';
        if (confirm(confirmMsg)) {
          authService.logout('login.html');
        }
      });
    }
  } else {
    authActionItem.innerHTML = `
      <a href="login.html" class="btn btn-primary nav-auth-btn" id="navLoginBtn" data-i18n="nav.farmer_login">
        ${loginText}
      </a>
    `;
  }
}

// Re-render auth state on language switch
window.addEventListener('agroguard:languageChanged', () => {
  initNavAuthState();
});

