/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
let registry = publicWidget.registry;

registry.SimilarProductView = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .te_similar_view': '_initSimilarProductView',
    },

    _initSimilarProductView: async function (ev) {
        ev.preventDefault();
        let element = ev.currentTarget;
        let product_id = $(element).attr('data-id');
        let params = {
            'product_id': product_id,
        }

        self = await $.get('/similar_products_item_data', params).then(function (data) {
           $("#similaroffcanvasWithBackdrop .offcanvas-body").html(data);
        });
    }
});