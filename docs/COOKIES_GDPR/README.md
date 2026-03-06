Cookies & GDPR - Map to GeoJSON Converter
==========================================
[TOC]

v0.0.7 - February 2026

---

# Introduction

This document outlines the cookie and GDPR compliance strategy for Map to GeoJSON Converter.

## Regulatory References

- [EU Cookies & GDPR](https://gdpr.eu/cookies/)
- [Data Protection under GDPR](https://europa.eu/youreurope/business/dealing-with-customers/data-protection/data-protection-gdpr/index_en.htm)
- [Understanding Cookies](https://web.dev/articles/understanding-cookies)
- [SameSite Cookies](https://web.dev/articles/samesite-cookie-recipes)

---

# Cookie Categories

## Essential (No Consent Required)

| Cookie | Purpose | Duration |
|--------|---------|----------|
| `cookieConsent` | Stores cookie preferences | 1 year |
| `sessionId` | Links user requests | Session |

## Analytics (Consent Required)

| Cookie | Purpose | Duration |
|--------|---------|----------|
| `Google Analytics` | Usage statistics | 2 years |

---

# Implementation

## Architecture

The cookie system is implemented in `webapp_modular`:

| File | Purpose |
|------|---------|
| `static/js/cookies.js` | `CookieManager` module - consent logic |
| `static/js/dom.js` | DOM references for banner elements |
| `static/index.html` | Cookie banner HTML |
| `static/privacy.html` | Privacy policy with cookie table and reset button |

## How It Works

1. **On first visit**: Banner appears with two options
2. **User chooses**: "Solo Essenziali" or "Accetta Tutti"
3. **Consent saved**: In `localStorage` with timestamp and version
4. **On return**: Consent is read and applied automatically
5. **Analytics**: Only enabled if user accepted all cookies

## Consent Data Structure

```javascript
// localStorage key: 'cookieConsent'
{
    essential: true,
    analytics: false,  // true if "Accept All"
    timestamp: "2026-02-15T10:30:00Z",
    version: "1.0"
}
```

## Key Methods

- `CookieManager.init()` - Initialize on app load
- `CookieManager.getConsent()` - Read stored consent
- `CookieManager.saveConsent(obj)` - Save user choice
- `CookieManager.hasConsent(type)` - Check specific consent
- `CookieManager.resetConsent()` - Clear and show banner again

---

# User Rights (GDPR)

| Right | Description |
|-------|-------------|
| Access | Know what data we have |
| Erasure | Request data deletion |
| Portability | Export data |
| Withdraw consent | Reset preferences anytime |

---

# Compliance Checklist

| Feature | Status |
|---------|--------|
| Cookie banner on first visit | ✅ |
| Two choices (Essential/Accept All) | ✅ |
| Privacy page with cookie table | ✅ |
| Analytics blocked until consent | ✅ |
| Reset consent button | ✅ |
| LocalStorage for consent | ✅ |
| Consent with timestamp | ✅ |
| Self-hosted fonts | ❌ (using Google Fonts) |

---

# References

- [GDPR Official Text](https://gdpr-info.eu/)
- [ICO Cookie Guidance](https://ico.org.uk/for-organisations/guide-to-pecr/cookies-and-similar-technologies/)
- [web.dev Cookie Documentation](https://web.dev/articles/understanding-cookies)
