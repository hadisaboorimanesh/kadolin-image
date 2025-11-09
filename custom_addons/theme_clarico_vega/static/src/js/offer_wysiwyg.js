/** @odoo-module **/
import { Wysiwyg } from '@web_editor/js/wysiwyg/wysiwyg';
import { patch } from "@web/core/utils/patch";

patch(Wysiwyg.prototype, {
    async _saveElement($el, context) {
        $el.find('.offcanvas_offer_popup').removeClass('show');
        $el.find('.offer_sidebar_offcanvas_button').css("right", "0");
        // Saving a view content
        await super._saveElement(...arguments);
    },
});
