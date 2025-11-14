/** @odoo-module **/

(function () {
    function loadNeshanSDK() {
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
                    tries += 1;
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

    function getCitySelection(form) {
        const sel = form.querySelector('select[name="city_id"]');
        const inp = form.querySelector('input[name="city"]');
        if (sel && sel.options && sel.selectedIndex >= 0) {
            const opt = sel.options[sel.selectedIndex];
            return { value: (opt.value || '').trim(), text: (opt.text || '').trim() };
        }
        if (inp) {
            return { value: (inp.value || '').trim(), text: (inp.value || '').trim() };
        }
        return { value: '', text: '' };
    }

//    function isTargetCitySelected(form, targetName, targetId) {
//        const cur = getCitySelection(form);
//        if (!cur.value && !cur.text) return false;
//        if (targetId && cur.value === String(targetId)) return true;
//        if (targetName && cur.text.includes(targetName)) return true;
//        return false;
//    }
function isTargetCitySelected(form, targetName, targetId) {
    const cur = getCitySelection(form);
    if (!cur.value && !cur.text) return false;

    if (targetId && cur.value === String(targetId)) return true;

    const text = (cur.text || "").trim();

    const isTehranOrKaraj = /تهران|Tehran|کرج|Karaj/i.test(text);
    if (isTehranOrKaraj) return true;

    if (targetName && text.includes(targetName)) return true;

    return false;
}

    function boot() {
        const form = document.querySelector('form[action*="/shop/address"]');
        if (!form) return;

        const wrapper = document.getElementById("neshan-map-wrapper");
        if (!wrapper) return;

        const mapDiv = document.getElementById("neshan-checkout-map");
        const apiKey = wrapper.dataset.apiKey || "";
        const targetName = wrapper.dataset.targetCityName || "تهران";
        const targetId = (wrapper.dataset.targetCityId || "").trim();
        const latInput = document.getElementById("partner_latitude");
        const lngInput = document.getElementById("partner_longitude");
        const msg = document.getElementById("map-required-msg");

        let map = null, marker = null, mapInitialized = false;

        function ensureMap() {
            if (mapInitialized) return;
            if (!apiKey) return;

            const lat0 = parseFloat(mapDiv.dataset.lat || "35.6892");
            const lng0 = parseFloat(mapDiv.dataset.lng || "51.3890");

            map = new L.Map("neshan-checkout-map", {
                key: apiKey,
                maptype: "neshan",
                poi: false,
                traffic: false,
                center: [isFinite(lat0) ? lat0 : 35.6892, isFinite(lng0) ? lng0 : 51.3890],
                zoom: 13,
            });

            function putMarker(lat, lng) {
                if (marker) marker.setLatLng([lat, lng]);
                else {
                    marker = L.marker([lat, lng], { draggable: true }).addTo(map);
                    marker.on("dragend", () => {
                        const p = marker.getLatLng();
                        latInput.value = p.lat.toFixed(7);
                        lngInput.value = p.lng.toFixed(7);
                        msg.classList.add("d-none");
                    });
                }
            }

            if (!isNaN(lat0) && !isNaN(lng0)) putMarker(lat0, lng0);

            map.on("click", (ev) => {
                const lat = +ev.latlng.lat.toFixed(7);
                const lng = +ev.latlng.lng.toFixed(7);
                latInput.value = lat;
                lngInput.value = lng;
                putMarker(lat, lng);
                msg.classList.add("d-none");
            });

            mapInitialized = true;
        }

        function showMap() {
            wrapper.style.display = "block";
            if (!mapInitialized) loadNeshanSDK().then(ensureMap).catch(() => {});
        }

        function hideMapAndClear() {
            wrapper.style.display = "none";
            latInput.value = "";
            lngInput.value = "";
            msg.classList.add("d-none");
        }

        function evalCity() {
            if (isTargetCitySelected(form, targetName, targetId)) showMap();
            else hideMapAndClear();
        }

        const sel = form.querySelector('select[name="city_id"]');
        const inp = form.querySelector('input[name="city"]');
        if (sel) sel.addEventListener("change", evalCity, true);
        if (inp) inp.addEventListener("input", evalCity, true);

        // ✅ اجباری کردن lat/lng اگر شهر تهران است
        form.addEventListener("submit", function (ev) {
            if (isTargetCitySelected(form, targetName, targetId)) {
                const latOk = latInput && latInput.value.trim() !== "";
                const lngOk = lngInput && lngInput.value.trim() !== "";
                if (!latOk || !lngOk) {
                    ev.preventDefault();
                    wrapper.style.display = "block";
                    msg.classList.remove("d-none");
                    msg.textContent = "لطفاً موقعیت خود را روی نقشه مشخص کنید (اجباری برای تهران)";
                    try { msg.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {}
                }
            }
        }, { capture: true });

        evalCity();
    }

    if (document.readyState === "complete" || document.readyState === "interactive") setTimeout(boot, 0);
    else window.addEventListener("DOMContentLoaded", boot);

    document.addEventListener("o_transition_completed", boot);
})();