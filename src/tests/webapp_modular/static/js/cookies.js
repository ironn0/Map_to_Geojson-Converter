/**
 * 🍪 Cookie Manager Module
 * Gestione del consenso cookie GDPR
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { el } from './dom.js';
import { toast } from './ui.js';

export const CookieManager = {
    /**
     * Inizializza il cookie manager
     */
    init() {
        if (!this.getConsent()) {
            this.showBanner();
        }
        this.setupListeners();
        this.applyConsent(this.getConsent());
    },
    
    /**
     * Mostra il banner cookie
     */
    showBanner() {
        if (el.cookieBanner) {
            el.cookieBanner.style.display = 'block';
        }
    },
    
    /**
     * Nasconde il banner cookie
     */
    hideBanner() {
        if (el.cookieBanner) {
            el.cookieBanner.style.display = 'none';
        }
    },
    
    /**
     * Setup event listeners
     */
    setupListeners() {
        if (el.cookieEssential) {
            el.cookieEssential.addEventListener('click', () => {
                this.saveConsent({ essential: true, analytics: false });
                this.hideBanner();
                toast('Preferenze cookie salvate', 'success');
            });
        }
        
        if (el.cookieAccept) {
            el.cookieAccept.addEventListener('click', () => {
                this.saveConsent({ essential: true, analytics: true });
                this.hideBanner();
                this.enableAnalytics();
                toast('Preferenze cookie salvate', 'success');
            });
        }
    },
    
    /**
     * Salva consenso cookie
     * @param {Object} consent - Oggetto consenso
     */
    saveConsent(consent) {
        localStorage.setItem('cookieConsent', JSON.stringify({
            ...consent,
            timestamp: new Date().toISOString(),
            version: '1.0'
        }));
    },
    
    /**
     * Ottiene consenso salvato
     * @returns {Object|null}
     */
    getConsent() {
        const saved = localStorage.getItem('cookieConsent');
        return saved ? JSON.parse(saved) : null;
    },
    
    /**
     * Applica il consenso salvato
     * @param {Object} consent - Oggetto consenso
     */
    applyConsent(consent) {
        if (!consent) return;
        
        if (!consent.analytics) {
            this.blockAnalytics();
        } else {
            this.enableAnalytics();
        }
    },
    
    /**
     * Blocca analytics
     */
    blockAnalytics() {
        window['ga-disable-G-XXXXXXX'] = true;
        console.log('[CookieManager] Analytics disabled');
    },
    
    /**
     * Abilita analytics
     */
    enableAnalytics() {
        window['ga-disable-G-XXXXXXX'] = false;
        console.log('[CookieManager] Analytics enabled');
    },
    
    /**
     * Resetta consenso
     */
    resetConsent() {
        localStorage.removeItem('cookieConsent');
        this.showBanner();
    },
    
    /**
     * Verifica se c'è consenso per un tipo
     * @param {string} type - Tipo di cookie
     * @returns {boolean}
     */
    hasConsent(type) {
        const consent = this.getConsent();
        return consent && consent[type] === true;
    }
};
