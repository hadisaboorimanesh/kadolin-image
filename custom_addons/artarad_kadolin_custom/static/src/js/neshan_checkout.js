/** @odoo-module **/

(function () {
    function loadNeshanLeaflet() {
        return new Promise((resolve, reject) => {
            if (window.L && L.Map) return resolve();

            const cssHref = "https://static.neshan.org/sdk/leaflet/v1.9.4/neshan-sdk/v1.0.8/index.css";
            if (!document.querySelector(`link[href="${cssHref}"]`)) {
                const link = document.createElement("link");
                link.rel = "stylesheet";
                link.href = cssHref;
                document.head.appendChild(link);
            }

            const jsSrc = "https://static.neshan.org/sdk/leaflet/v1.9.4/neshan-sdk/v1.0.8/index.js";
            if (document.querySelector(`script[src="${jsSrc}"]`)) {
                let tries = 0;
                const t = setInterval(() => {
                    tries++;
                    if (window.L && L.Map) { clearInterval(t); resolve(); }
                    else if (tries > 60) { clearInterval(t); reject(new Error("Neshan SDK not ready")); }
                }, 100);
                return;
            }
            const s = document.createElement("script");
            s.src = jsSrc;
            s.async = true;
            s.onload = () => resolve();
            s.onerror = () => reject(new Error("Neshan SDK load failed"));
            document.head.appendChild(s);
        });
    }

    function setupSubmitHook() {
        const form = document.querySelector('form[action*="/shop/address"]');
        if (!form) return;

        const latInput = form.querySelector('input[name="partner_latitude"]');
        const lngInput = form.querySelector('input[name="partner_longitude"]');
        const modeInput = form.querySelector('input[name="mode"], select[name="mode"]');

        if (form.__neshanBound) return;
        form.__neshanBound = true;

        form.addEventListener('submit', function (ev) {
            const lat = latInput && latInput.value ? latInput.value : null;
            const lng = lngInput && lngInput.value ? lngInput.value : null;
            if (!lat && !lng) return; // مختصات نداریم، فرم طبق روال برود

            ev.preventDefault(); // اول lat/lng را روی پارتنر بنویسیم
            const mode = modeInput ? modeInput.value : 'billing';

            fetch('/shop/set_latlng', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: { lat: lat, lng: lng, mode: mode },
                }),
                keepalive: true,
            }).catch(() => {}).finally(() => {
                form.submit(); // بعد از تلاش، فرم را بفرست
            });
        }, { capture: true });
    }

    function initMap() {
        const el = document.getElementById("neshan-checkout-map");
        if (!el) return;

        const apiKey = el.dataset.apiKey || "";
        if (!apiKey) return; // بدون کلید نمایش نمی‌دهیم

        const lat0 = parseFloat(el.dataset.lat || "35.6892"); // پیش‌فرض تهران
        const lng0 = parseFloat(el.dataset.lng || "51.3890");

        const form = document.querySelector('form[action*="/shop/address"]');
        const latInput = form && form.querySelector('input[name="partner_latitude"]');
        const lngInput = form && form.querySelector('input[name="partner_longitude"]');

        // پاک‌سازی هر src/href مشکوک که ممکن است قبلاً اشتباه تزریق شده باشد
        ["neshan", "standard-day", "standard-night", "osm-bright", "dreamy"].forEach((bad) => {
            document.querySelectorAll(`[src="${bad}"], [href="${bad}"]`).forEach((n) => {
                n.parentNode && n.parentNode.removeChild(n);
            });
        });

        const map = new L.Map("neshan-checkout-map", {
            key: apiKey,
            maptype: "neshan",  // می‌توانی standard-day/night هم بگذاری
            poi: false,
            traffic: false,
            center: [lat0, lng0],
            zoom: 14,
        });

        let marker = null;
        function putMarker(lat, lng) {
            if (marker) marker.setLatLng([lat, lng]);
            else {
                marker = L.marker([lat, lng], { draggable: true }).addTo(map);
                marker.on("dragend", () => {
                    const p = marker.getLatLng();
                    if (latInput) latInput.value = p.lat.toFixed(7);
                    if (lngInput) lngInput.value = p.lng.toFixed(7);
                });
            }
        }

        if (!isNaN(lat0) && !isNaN(lng0)) {
            putMarker(lat0, lng0);
        }

        map.on("click", (ev) => {
            const lat = +ev.latlng.lat.toFixed(7);
            const lng = +ev.latlng.lng.toFixed(7);
            if (latInput) latInput.value = lat;
            if (lngInput) lngInput.value = lng;
            putMarker(lat, lng);
        });

        setupSubmitHook();
    }

    function boot() {
        const el = document.getElementById("neshan-checkout-map");
        if (!el) return;
        loadNeshanLeaflet().then(initMap).catch(() => {});
    }

    if (document.readyState === "complete" || document.readyState === "interactive") setTimeout(boot, 0);
    else window.addEventListener("DOMContentLoaded", boot);
    document.addEventListener("o_transition_completed", boot);
})();