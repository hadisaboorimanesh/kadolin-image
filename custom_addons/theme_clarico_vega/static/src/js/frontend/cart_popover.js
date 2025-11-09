/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
let registry = publicWidget.registry;

registry.websiteSaleCartLinkEpt = publicWidget.Widget.extend({
    selector: '.o_wsale_my_cart #main_cart_popover_content',
    events: {
        'click': '_cartPopupData',
    },
    _cartPopupData: async function(ev) {
        ev.preventDefault();
        self = await $.get('/shop/cart_popover').then(function (data) {
            $("#cartoffcanvasWithBackdrop .offcanvas-body").html(data);
            $(".te_clear_cart_popover").on('click', function(ev) {
                rpc('/shop/clear_cart', {}).then(function (data) {
                    location.reload();
                    $(".my_cart_quantity").html('0');
                });
            });
        });
    },
});

/*==== clear cart ========*/
registry.clear_cart = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .te_clear_cart': '_onClickClearCart',
    },
    _onClickClearCart: function (ev) {
        ev.preventDefault();
        rpc('/shop/clear_cart', {}).then(function(data){
            location.reload();
        });
    },
});
