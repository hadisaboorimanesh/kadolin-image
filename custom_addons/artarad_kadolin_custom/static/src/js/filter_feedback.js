/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";

/**
 * ایده: بعد از هر اسکن (اغلب اسکنر Enter می‌زنند) یا وقتی DOM لیست تغییر کرد،
 * امضای وضعیت لیست را با قبلی مقایسه می‌کنیم؛ اگر تعداد ردیف‌ها کم شد
 * یا عبارت جستجو عوض شد ⇒ فیلتر رخ داده ⇒ بوق + فلش بنر.
 */

(function () {
    // --- Beep بدون نیاز به فایل صوتی ---
    function beep(duration = 140, frequency = 880) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.value = frequency;
            osc.connect(gain);
            gain.connect(ctx.destination);
            gain.gain.setValueAtTime(0.0001, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.22, ctx.currentTime + 0.02);
            osc.start();
            setTimeout(() => {
                gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.02);
                osc.stop();
                ctx.close();
            }, duration);
        } catch (e) {
            // ممکنه مرورگر بلاک کنه؛ اشکالی ندارد
        }
    }

    // --- بنر کوچیک بالای صفحه ---
    function flashBanner(text) {
        let el = document.querySelector("#akc-filter-flash");
        if (!el) {
            el = document.createElement("div");
            el.id = "akc-filter-flash";
            el.className = "akc-filter-flash";
            document.body.appendChild(el);
        }
        el.textContent = text || _t("Filtered by scanned code");
        el.classList.add("show");
        setTimeout(() => el.classList.remove("show"), 900);
    }

    // امضای وضعیت لیست/سرچ
    function signatureOfCurrentList() {
        // لیست مخصوص صفحه بارکد PACK؛ اگر نبود، هر لیست فعال
        const list =
            document.querySelector(".o_stock_barcode_main_content .o_list_view tbody") ||
            document.querySelector(".o_action_manager .o_list_view tbody");
        const rows = list ? list.querySelectorAll("tr:not(.o_list_no_result)") : [];
        const count = rows ? rows.length : 0;
        const searchInput = document.querySelector(".o_control_panel .o_searchview_input");
        const q = searchInput ? (searchInput.value || "") : "";
        return `${count}|${q}`;
    }

    let prevSignature = null;

    function detectAndNotify() {
        const nowSig = signatureOfCurrentList();
        if (prevSignature === null) {
            prevSignature = nowSig;
            return;
        }
        const [prevCountStr, prevQ] = prevSignature.split("|");
        const [nowCountStr, nowQ] = nowSig.split("|");
        const prevCount = parseInt(prevCountStr || "0");
        const nowCount = parseInt(nowCountStr || "0");

        const filtered = (nowCount >= 0 && prevCount >= 0 && nowCount < prevCount) || (nowQ !== prevQ);
        if (filtered) {
            beep(); // یه بیپ کوتاه
            flashBanner(_t("Filtered by scanned code")); // بنر
        }
        prevSignature = nowSig;
    }

    // بعد از اسکن/Enter، چندبار چک کن چون UI async آپدیت می‌شود
    function scheduleCheck() {
        setTimeout(detectAndNotify, 60);
        setTimeout(detectAndNotify, 150);
        setTimeout(detectAndNotify, 300);
    }

    // 1) ساده‌ترین راه: اکثر اسکنرها Enter می‌فرستند
    document.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") {
            scheduleCheck();
        }
    });

    // 2) اگر DOM لیست عوض شد (مثلاً سرچ/فیلتر)، خودکار تشخیص بده
    const obs = new MutationObserver(() => {
        // تغییرات ریز متعدد میاد؛ با تاخیر کم debounce کنیم
        scheduleCheck();
    });
    window.addEventListener("load", () => {
        // امضا اولیه
        setTimeout(() => {
            prevSignature = signatureOfCurrentList();
            const target =
                document.querySelector(".o_stock_barcode_main_content") ||
                document.querySelector(".o_action_manager");
            if (target) {
                obs.observe(target, { childList: true, subtree: true });
            }
        }, 400);
    });
})();
