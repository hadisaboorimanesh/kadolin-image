/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import "@website/js/editor/snippets.options";

options.registry.WebsiteSaleProductsItem.include({

    willStart: async function () {

        let def = this._super(...arguments);
        this.ribbonPositionClasses = {
            'left': 'o_ribbon_left',
            'right': 'o_ribbon_right',
            'o_product_label_style_1_left': 'o_product_label_style_1_left',
            'o_product_label_style_1_right': 'o_product_label_style_1_right',
            'o_product_label_style_2_left': 'o_product_label_style_2_left',
            'o_product_label_style_2_right': 'o_product_label_style_2_right',
            'o_product_label_style_3_left': 'o_product_label_style_3_left',
            'o_product_label_style_3_right': 'o_product_label_style_3_right',
            'o_product_label_style_4_left': 'o_product_label_style_4_left',
            'o_product_label_style_4_right': 'o_product_label_style_4_right',
        };
        return def
    },

    async setRibbonPosition(previewMode, widgetValue, params) {
         const allowedValues = ['left', 'right', 'o_ribbon_left', 'o_ribbon_right',
         'o_product_label_style_1_left','o_product_label_style_2_left', 'o_product_label_style_3_left',
         'o_product_label_style_4_left', 'o_product_label_style_1_right','o_product_label_style_2_right',
         'o_product_label_style_3_right', 'o_product_label_style_4_right'];
         const ribbonPositions = {
            left: 'o_ribbon_left',
            right: 'o_ribbon_right',
         };

         widgetValue = ribbonPositions[widgetValue] || widgetValue;
         const ribbonPosition = allowedValues.includes(widgetValue) ? widgetValue : 'left';
         this.$ribbon[0].classList.remove(...allowedValues);
         this.$ribbon[0].classList.add(ribbonPosition);
         await this._saveRibbon();
    },

    async _computeWidgetState(methodName, params) {
        const classList = this.$ribbon[0].classList;
        switch (methodName) {
            case 'setRibbon':
                return this.$target.attr('data-ribbon-id') || '';
            case 'setRibbonName':
                return this.$ribbon.text();
            case 'setRibbonPosition': {
                if (classList.contains('o_product_label_style_1_left')){
                    return 'o_product_label_style_1_left';
                } else if (classList.contains('o_product_label_style_2_left')){
                    return 'o_product_label_style_2_left';
                } else if (classList.contains('o_product_label_style_3_left')){
                    return 'o_product_label_style_3_left';
                } else if (classList.contains('o_product_label_style_4_left')){
                    return 'o_product_label_style_4_left';
                } else if (classList.contains('o_product_label_style_1_right')){
                    return 'o_product_label_style_1_right';
                } else if (classList.contains('o_product_label_style_2_right')){
                    return 'o_product_label_style_2_right';
                } else if (classList.contains('o_product_label_style_3_right')){
                    return 'o_product_label_style_3_right';
                } else if (classList.contains('o_product_label_style_4_right')){
                    return 'o_product_label_style_4_right';
                } else if (classList.contains('o_ribbon_left')) {
                    return 'left';
                }
                return 'right';
            }
        }
        return this._super(methodName, params);
    },
//
    async _saveRibbon(isNewRibbon = false) {
        const text = this.$ribbon.text().trim();
        const ribbonClass = this.$ribbon.attr('class') || '';
        const match1 = ribbonClass.match(/o_product_label_style_(\d+)_(left|right)/);
        const match2 = ribbonClass.match(/o_ribbon_(left|right)/);

        const result = (match1 ? match1[0] : null) || (match2 ? match2[0] : null);
        const ribbon = {
            'name': text,
            'bg_color': this.$ribbon[0].style.backgroundColor,
            'text_color': this.$ribbon[0].style.color,
            'position': result,
        };
        ribbon.id = isNewRibbon ? Date.now() : parseInt(this.$target.closest('.oe_product')[0].dataset.ribbonId);
        this.trigger_up('set_ribbon', {ribbon: ribbon});
        this.ribbons = await new Promise(resolve => this.trigger_up('get_ribbons', {callback: resolve}));
        this.rerender = true;
        await this._setRibbon(ribbon.id);
    },

    async _setRibbon(ribbonId) {
        this.$target[0].dataset.ribbonId = ribbonId;
        this.trigger_up('set_product_ribbon', {
            templateId: this.productTemplateID,
            ribbonId: ribbonId || false,
        });
        const ribbon = (
            this.ribbons[ribbonId] ||
            {name: '', bg_color: '', text_color: '', position: 'left'}
        );
        const $editableDocument = $(this.$target[0].ownerDocument.body);
        const $ribbons = $editableDocument.find(`[data-ribbon-id="${ribbonId}"] .o_ribbon`);
        $ribbons.empty().append(ribbon.name);
        let htmlClasses;
        this.trigger_up('get_ribbon_classes', {callback: classes => htmlClasses = classes});
        $ribbons.removeClass(htmlClasses);
        /* Update key if getting left/right position */
        const positionMap = {
            'o_ribbon_left': 'left',
            'o_ribbon_right': 'right'
        };
        ribbon.position = positionMap[ribbon.position] || ribbon.position;

        $ribbons.addClass(this.ribbonPositionClasses[ribbon.position]);
        $ribbons.css('background-color', ribbon.bg_color || '');
        $ribbons.css('color', ribbon.text_color || '');

        if (!this.ribbons[ribbonId]) {
            $editableDocument.find(`[data-ribbon-id="${ribbonId}"]`).each((index, product) => delete product.dataset.ribbonId);
        }
        this.$ribbon.addClass('o_dirty');
    },
});

