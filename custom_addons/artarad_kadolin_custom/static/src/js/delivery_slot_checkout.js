/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
const { DateTime } = luxon;

// ---- Debug helpers ----
const DS = "[DS]";
function dlog(...args) { try { console.log(DS, ...args); } catch(_) {} }

const persianFmt = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    weekday: "short",
    day: "2-digit",
    month: "short",
});

function formatPersian(d) {
    const parts = persianFmt.formatToParts(d);
    const bag = {};
    for (const p of parts) bag[p.type] = p.value;
    return {
        weekday: bag.weekday || "",
        day: bag.day || "",
        month: bag.month || "",
    };
}

// Helper: event delegation
function onDoc(eventType, selector, handler) {
    const listener = (ev) => {
        let el = ev.target;
        while (el && el !== document) {
            if (el.matches && el.matches(selector)) {
                handler(ev, el);
                break;
            }
            el = el.parentElement;
        }
    };
    document.addEventListener(eventType, listener, true);
    return () => {
//        dlog("onDoc(): unbinding", { eventType, selector });
        document.removeEventListener(eventType, listener, true);
    };
}

publicWidget.registry.KadolinDeliverySlot = publicWidget.Widget.extend({
    /**
     * DEBUG NOTE:
     * All lifecycle and RPC checkpoints print with the [DS] prefix.
     */
    selector: "#delivery_slot_block",

    //----------------------------------------------------------------------
    // Lifecycle
    //----------------------------------------------------------------------
    willStart: function () {
//        dlog("willStart()");
        // فقط برای اطمینان از لود اولیه بدون async/await
//        dlog("willStart(): end");
        return Promise.resolve();
    },

    start: function () {
//        dlog("start(): begin", { el: this.el });
        this._unbinders = [];
//        dlog("start(): _unbinders initialized");
        this._lastCity = "";
//        dlog("start(): _lastCity initialized to empty string");
        this._isTehran = false;          // پیش‌فرض: نه
        const widget = this;
        // هر بار که کاربر آدرس یا روش ارسال را تغییر دهد → بررسی مجدد
//        dlog("start(): binding click on address_card");
//        this._unbinders.push(onDoc("click", "div[name='address_card']", async () => {
//                setTimeout(() => this._refresh(true), 400);
//           }));

        this._unbinders.push(onDoc("click", "div[name='address_card']", (ev, el) => {
            const city = (el && el.dataset && el.dataset.city) ? el.dataset.city.trim() : "";
            this._refresh(true, city);   // city را مستقیم پاس می‌دهیم
        }));
// جلوگیری از ادامه checkout بدون انتخاب روز و اسلات
this._unbinders.push(onDoc("click", "a[href='/shop/confirm_order'], #o_payment_form_pay", (ev) => {
    // اگر تهران نیست اصلاً محدودیتی اعمال نکن
    // (یا اگر بلوک اسلات‌ها مخفی است، یعنی تهران نیست یا لازم نیست)
    const isBlockVisible = !!document.querySelector("#delivery_slot_block:not(.d-none)");
    if (!(widget._isTehran && isBlockVisible)) {
        return; // اجازه بده ادامه دهد
    }

    const dateEl = document.querySelector("#delivery_date_input");
    const slotEl = document.querySelector("#delivery_slot_input");

    const dateVal = (dateEl && typeof dateEl.value === 'string') ? dateEl.value.trim() : "";
    const slotVal = (slotEl && typeof slotEl.value === 'string') ? slotEl.value.trim() : "";


//    let needSlot = false;
//    let slotVal = "";
//    if (slotEl && !slotEl.disabled && slotEl.offsetParent !== null) {
//        needSlot = true;
//        slotVal = (typeof slotEl.value === 'string') ? slotEl.value.trim() : "";
//    }


    if (!dateVal ||  !slotVal) {
        ev.preventDefault();
        alert(!dateVal ? "لطفاً ابتدا روز تحویل را انتخاب کنید."
                       : "لطفاً بازه‌ی زمانی تحویل را هم انتخاب کنید.");
        return false;
    }
}));



this._unbinders.push(onDoc("change", "input[name='o_delivery_radio']", async () => {
    setTimeout(() => this._refresh(true), 400);
}));
this._unbinders.push(onDoc("click", "label.o_delivery_carrier_label", async () => {
    setTimeout(() => this._refresh(true), 400);
}));

// وقتی اسلات تغییر کرد: قبل از ذخیره، حتماً روز انتخاب شده باشد
this._unbinders.push(onDoc("change", "input[name='delivery_slot']", (ev) => {
    const input = ev.target;
    const slot = input && input.value;
    const dateInput = this.el.querySelector("#delivery_date_input");
    const selectedDate = dateInput ? dateInput.value : "";

    if (!selectedDate) {
        // روز انتخاب نشده → اسلات را از حالت انتخاب خارج کن و پیام بده
        if (input) input.checked = false;
        alert("لطفاً ابتدا روز تحویل را انتخاب کنید.");
        return;
    }

    // روز داریم → ذخیره‌ی روز+اسلات روی سفارش
    rpc("/shop/delivery_slot", { date_str: selectedDate, slot: slot })
        .then((resp) => {
            if (resp && resp.ok === true) {
                // برای اطمینان از موجود بودن مقدار در فرم
                const slotHidden = this.el.querySelector("#delivery_slot_input");
                if (slotHidden) slotHidden.value = slot;
            } else {
                if (input) input.checked = false;
                alert("ذخیره بازه ساعتی ناموفق بود. لطفاً دوباره تلاش کنید.");
            }
        })
        .catch(() => {
            if (input) input.checked = false;
            alert("خطا در ارتباط با سرور هنگام ذخیره بازه ساعتی.");
        });
}));
        // اولین بار هم چک کن
//        dlog("start(): first _refresh(true) call");
        this._refresh(true);

//        dlog("start(): calling _super()");
        return this._super.apply(this, arguments);
 },

    destroy: function () {
//        dlog("destroy(): begin", { unbinders: (this._unbinders || []).length });
        (this._unbinders || []).forEach((u) => {
            try {
                u();
            } catch {}
        });
//        dlog("destroy(): calling _super()");
        return this._super.apply(this, arguments);
    },

    //----------------------------------------------------------------------
    // Core logic
    //----------------------------------------------------------------------
//    _refresh: function (force) {
//        const self = this;
//
//        setTimeout(async function () {
//            if (!self.el || !document.body.contains(self.el)) return;
//
//            let city = "";
//            try {
//                const resp = await rpc("/shop/current_shipping_city", {});
//                city = (resp && (resp.city || (resp.result && resp.result.city))) || "";
//            } catch (_) {}
//
//            const isTehran = /تهران|Tehran|کرج|Karaj/i.test(city);
//            self.el.classList.toggle("d-none", !isTehran);
//
//            if (!isTehran) {
//                return;
//            }
//             self._isTehran = isTehran;
//            const changed = self._lastCity !== city;
//            self._lastCity = city;
//            const needRender = force || changed || !self.el.querySelector(".ds-day");
//            if (needRender) {
//                self._renderDays();
//            }
//        }, 150);
//
//
//    },


    _refresh: function (force, presetCity) {
    const self = this;

    // دیگه setTimeout داخلی لازم نداریم، بیرونی‌ها اگر خواستی خودت نگه‌دار
    (async function () {
        if (!self.el || !document.body.contains(self.el)) {
            return;
        }

        // ۱) اگر از DOM شهر را گرفته‌ایم، از همان استفاده کن
        let city = (presetCity || "").trim();

        // ۲) اگر presetCity نداشتیم (مثلاً اولین بار در start یا تغییر carrier)
        // از RPC قبلی استفاده می‌کنیم
        if (!city) {
            try {
                const resp = await rpc("/shop/current_shipping_city", {});
                city = (resp && (resp.city || (resp.result && resp.result.city))) || "";
            } catch (_) {
                city = "";
            }
        }

        const isTehran = /تهران|Tehran|کرج|Karaj/i.test(city);
        self._isTehran = isTehran;   // حتماً state داخلی را ست کن
        self.el.classList.toggle("d-none", !isTehran);

        if (!isTehran) {
            return;
        }

        const changed = self._lastCity !== city;
        self._lastCity = city;
        const needRender = force || changed || !self.el.querySelector(".ds-day");
        if (needRender) {
            self._renderDays();
        }
    })();
},

    _renderDays: function () {
    const cont = this.el.querySelector("#ds-days");
    if (!cont) return;

    cont.innerHTML = `<div class="text-muted small">در حال بارگذاری...</div>`;

    rpc("/shop/delivery_availability", { days: 10 })
        .then((days) => {
            cont.innerHTML = "";
            (days || []).forEach((rec) => {
                // --- حذف جمعه‌ها (Luxon: Monday=1 ... Sunday=7، پس Friday=5)
                const dt = DateTime.fromISO(rec.date, { zone: "Asia/Tehran" });
                if (dt.weekday === 5) {
                    return; // این روز جمعه است → ردش کن
                }

                const d = new Date(rec.date);
                const parts = formatPersian(d);

                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "ds-day btn text-center py-2 w-100";
                btn.dataset.date = rec.date;

                btn.innerHTML = `
                    <div class="small">${parts.weekday}</div>
                    <div class="fw-bold fs-5">${parts.day}</div>
                    <div class="small">${parts.month}</div>
                `;

                if (rec.full) {
                    btn.classList.add("btn-outline-danger");
                    btn.disabled = true;
                    btn.title = "ظرفیت تکمیل است";
                } else {
                    btn.classList.add("btn-outline-secondary");
                    btn.addEventListener("click", (ev) => this._onClickDay(ev));
                }
                cont.appendChild(btn);
            });
        })
        .catch(() => {
            cont.innerHTML = `<div class="text-danger small">خطا در دریافت ظرفیت روزها</div>`;
        });
},

    /**
     * Pick the first available time slot (if any) and fire a 'change' so that
     * any listeners/onchange handlers run. Supports <select>, radio group,
     * and a plain input (hidden/text) with data-default.
     * @returns {boolean} true if a slot was selected
     */
    _selectFirstAvailableSlot: function () {
        const root = this.el || document;
        const slotEl = root.querySelector("#delivery_slot_input");
        if (!slotEl || slotEl.disabled || slotEl.offsetParent === null) {
            return false; // no visible/active slot input → nothing to do
        }

        let selected = false;

        // Case 1: <select id="delivery_slot_input">...</select>
        if (slotEl.tagName === "SELECT") {
            const opt = Array.from(slotEl.options || []).find(o => !o.disabled && o.value && o.value.trim() !== "");
            if (opt) {
                slotEl.value = opt.value;
                slotEl.dispatchEvent(new Event("change", { bubbles: true }));
                selected = true;
            }
        } else {
            // Case 2: radio group: <input type="radio" name="delivery_slot_input" ...>
            const radios = root.querySelectorAll("input[type='radio'][name='delivery_slot_input']");
            if (radios && radios.length) {
                const active = Array.from(radios).find(r => !r.disabled && r.offsetParent !== null);
                if (active) {
                    active.checked = true;
                    active.dispatchEvent(new Event("change", { bubbles: true }));
                    selected = true;
                }
            } else {
                // Case 3: fallback hidden/text input with data-default
                const def = slotEl.dataset.default || slotEl.getAttribute("data-default") || "";
                if (!slotEl.value && def) {
                    slotEl.value = def;
                    slotEl.dispatchEvent(new Event("change", { bubbles: true }));
                    selected = true;
                }
            }
        }
        return selected;
    },

    _onClickDay: function (ev) {
//        dlog("_onClickDay(): clicked", { target: ev.currentTarget, date: ev.currentTarget && ev.currentTarget.dataset ? ev.currentTarget.dataset.date : undefined });
        const btn = ev.currentTarget;
        const val = btn.dataset.date;
//        dlog("_onClickDay(): value", val);
        const all = this.el.querySelectorAll(".ds-day");

        all.forEach((b) => {
            b.classList.remove("active", "btn-primary", "text-white");
            b.classList.add("btn-outline-secondary");
        });
        // اگر از قبل اسلاتی انتخاب شده بود، مقدار hidden را هم هماهنگ کن
const slotChecked = this.el.querySelector("input[name='delivery_slot']:checked");
const slotHidden = this.el.querySelector("#delivery_slot_input");
if (slotChecked && slotHidden) {
    slotHidden.value = slotChecked.value;
}

//        dlog("_onClickDay(): RPC /shop/delivery_slot start", { date_str: val });
        rpc("/shop/delivery_slot", { date_str: val })
            .then((resp) => {
//                dlog("_onClickDay(): RPC success", resp);
                if (!resp || resp.ok !== true) {
//                    dlog("_onClickDay(): not ok", resp);
                    if (resp && resp.error === "capacity_reached") {
//                        dlog("_onClickDay(): capacity reached for", val);
                        btn.classList.remove("btn-outline-secondary");
                        btn.classList.add("btn-outline-danger");
                        btn.disabled = true;
                        alert("ظرفیت تحویل در این تاریخ تکمیل شده است. لطفاً روز دیگری را انتخاب کنید.");
                    }
                    return;
                }

                btn.classList.add("active", "btn-primary", "text-white");
                btn.classList.remove("btn-outline-secondary");
                const input = this.el.querySelector("#delivery_date_input");
                if (input) input.value = val;
                // Ensure a time slot is also selected when a day is picked
                this._selectFirstAvailableSlot();
//                dlog("_onClickDay(): selection applied", { date: val });
            })
            .catch((err) => { dlog("_onClickDay(): RPC error", err); });
    },
});

