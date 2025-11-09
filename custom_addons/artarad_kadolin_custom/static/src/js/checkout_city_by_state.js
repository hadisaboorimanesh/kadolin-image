/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.KadolinCheckoutCity = publicWidget.Widget.extend({
    selector: 'form[action*="/shop/address/submit"]',
    start() {
        this.stateEl   = this.el.querySelector('#o_state_id');
        this.citySelect = this.el.querySelector('#o_city_select');  // name="city_id"
        this.cityHidden = this.el.querySelector('#o_city');          // name="city"
        if (this.stateEl && this.citySelect && this.cityHidden) {
            this._bind();
            // پیش‌بارگذاری برای حالت ویرایش
            const presetStateId = this.stateEl.value;
            const presetCityName = this.cityHidden.value;
            const presetCityId = this.citySelect.value; // اگر از قبل چیزی روی city_id ست بود
            if (presetStateId) {
                this._reloadCities(presetStateId, { selectedId: presetCityId, selectedName: presetCityName });
            }
            this._syncHiddenFromSelect(); // یکبار سینک اولیه
        }
        return this._super(...arguments);
    },

    _bind() {
        this.stateEl.addEventListener('change', (ev) => {
            const stateId = ev.target.value;
            this._reloadCities(stateId);
        });
        this.citySelect.addEventListener('change', () => this._syncHiddenFromSelect());
    },

    async _reloadCities(stateId, preset = {}) {
        this.citySelect.innerHTML = '<option value="">در حال بارگذاری...</option>';
        this._setHiddenCity('');
        if (!stateId) {
            this.citySelect.innerHTML = '<option value="">ابتدا استان را انتخاب کنید</option>';
            return;
        }
        try {
            const resp = await fetch(`/shop/cities?state_id=${encodeURIComponent(stateId)}`);
            const data = await resp.json(); // [{id, name}]
            this.citySelect.innerHTML = '<option value="">انتخاب شهر...</option>';
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = String(c.id);       // value = id
                opt.textContent = c.name;       // متن = نام
                // پیش‌انتخاب: اگر id موجود نبود با name مَچ کن
                if ((preset.selectedId && String(preset.selectedId) === String(c.id)) ||
                    (!preset.selectedId && preset.selectedName && preset.selectedName === c.name)) {
                    opt.selected = true;
                }
                this.citySelect.appendChild(opt);
            });
            this._syncHiddenFromSelect();
        } catch (err) {
            this.citySelect.innerHTML = '<option value="">خطا در دریافت شهرها</option>';
        }
    },

    _syncHiddenFromSelect() {
        const opt = this.citySelect.options[this.citySelect.selectedIndex];
        const label = opt ? opt.textContent : '';
        this._setHiddenCity(label);
    },

    _setHiddenCity(value) {
        this.cityHidden.value = value || '';
    },
});