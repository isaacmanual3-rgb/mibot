/**
 * Aero Flex - Device UUID (identificación única por navegador)
 *
 * En vez de un fingerprint de canvas/webgl (que COLISIONA entre teléfonos
 * del mismo modelo), usamos un UUID aleatorio único por navegador, guardado
 * en localStorage Y cookie con auto-reparación. Así dos personas con el mismo
 * modelo de celular tienen UUIDs distintos y no se marcan como multicuenta.
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'device_uuid';
    var COOKIE_KEY = 'device_uuid';

    // Genera un UUID v4 aleatorio
    function genUUID() {
        if (window.crypto && crypto.randomUUID) {
            try { return 'df_' + crypto.randomUUID().replace(/-/g, '').slice(0, 24); } catch (e) {}
        }
        // Fallback
        var s = '';
        var chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
        for (var i = 0; i < 24; i++) s += chars[Math.floor(Math.random() * chars.length)];
        return 'df_' + s;
    }

    // Leer/escribir cookie
    function setCookie(name, value, days) {
        var d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = name + '=' + value + ';expires=' + d.toUTCString() + ';path=/;SameSite=Lax';
    }
    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    }

    // Obtener el UUID del dispositivo (con auto-reparación entre localStorage y cookie)
    function getDeviceUUID() {
        var fromLS = null, fromCookie = getCookie(COOKIE_KEY);
        try { fromLS = localStorage.getItem(STORAGE_KEY); } catch (e) {}

        var uuid = fromLS || fromCookie;
        if (!uuid) {
            uuid = genUUID();
        }
        // Auto-reparación: asegurar que ambos almacenes tengan el mismo valor
        try { if (fromLS !== uuid) localStorage.setItem(STORAGE_KEY, uuid); } catch (e) {}
        if (fromCookie !== uuid) setCookie(COOKIE_KEY, uuid, 3650); // 10 años

        return uuid;
    }

    // Enviar el UUID al servidor
    function sendToServer(userId) {
        var uuid = getDeviceUUID();
        try {
            fetch('/api/device-check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    user_id: userId,
                    device_hash: uuid
                })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                // Si el servidor baneó por dispositivo+IP, recargar para mostrar la pantalla de baneo
                if (data && data.banned) {
                    window.location.reload();
                }
            })
            .catch(function () { /* silencioso */ });
        } catch (e) { /* silencioso */ }
    }

    // Obtener el user_id de Telegram o de la URL (?user_id=... o ?u=...)
    function resolveUserId() {
        try {
            if (window.Telegram && window.Telegram.WebApp) {
                var tg = window.Telegram.WebApp;
                var u = tg.initDataUnsafe && tg.initDataUnsafe.user;
                if (u && u.id) return String(u.id);
            }
        } catch (e) {}
        try {
            var p = new URLSearchParams(window.location.search);
            return p.get('user_id') || p.get('u') || null;
        } catch (e) {}
        return null;
    }

    // Disparar en cuanto haya un user_id disponible
    function init() {
        var uid = resolveUserId();
        if (uid) {
            sendToServer(uid);
        } else {
            // Reintentar un par de veces por si Telegram tarda en cargar
            var tries = 0;
            var iv = setInterval(function () {
                tries++;
                var id = resolveUserId();
                if (id) { clearInterval(iv); sendToServer(id); }
                else if (tries >= 10) { clearInterval(iv); }
            }, 500);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exponer para uso manual si se necesita
    window.DeviceUUID = { get: getDeviceUUID, send: sendToServer };
})();
