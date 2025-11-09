/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { WebsiteSale } from '@website_sale/js/website_sale';
import { patch } from "@web/core/utils/patch";
let registry = publicWidget.registry;

registry.QuickView = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .quick-view-a': '_initQuickView',
        'click .ajax_cart_popup': '_initQuickView',
        'click .quick_close':'_quick_close',
    },
    _initQuickView: function(ev){
        ev.preventDefault()
        let element = ev.currentTarget;
        let product_id = $(element).attr('data-id');
        let params = {
            'product_id': product_id,
        }
        if (product_id){
            if($(ev.currentTarget).hasClass('quick-view-a')){
                $("#quick_view_model_shop .modal-body").addClass('quick_view_clicked');
            }
            rpc('/quick_view_item_data', params).then((data) => {
                $("#quick_view_model .modal-body").html(data);
                $('#quick_view_model').modal('show');
                $('[data-bs-toggle="tooltip"]').tooltip({animation: true,delay: {show: 300,hide: 100} })
            });
        }
    },
    _quick_close: function(){
        $('#quick_view_model_shop, #quick_view_model, #quick_view_model_popup').modal('hide');
        $("#quick_view_model_shop .modal-body, #quick_view_model .modal-body").html('');
    },
});

/*override base method and remove quick view popup because optional product popup was not editable when quick view is render*/
patch(WebsiteSale.prototype, {
    _onClickAdd(ev){
        $('#quick_view_model_shop, #quick_view_model, #quick_view_model_popup').modal('hide');
        $("#quick_view_model_shop .modal-body, #quick_view_model .modal-body").html('');
        return super._onClickAdd(...arguments);
    },
});
