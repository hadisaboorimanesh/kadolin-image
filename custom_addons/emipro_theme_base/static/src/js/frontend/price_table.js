/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";


WebsiteSale.include({

    events: Object.assign(WebsiteSale.prototype.events, {
        'click .cart_line .js_add_cart_json': '_onChangeCartQuantity',
        'change .cart_line input.js_quantity[data-product-id]': '_onChangeCartQuantity',
        'click .cart_line .js_delete_product': '_onClickRemoveItem',
        'click .js_delete_product_kadolin': '_onClickRemoveItemKadolin',
    }),
     async _onClickRemoveItemKadolin(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const $btn = $(ev.currentTarget);
        const $line = $btn.closest("[data-product-id]");
        const productId = parseInt($line.data("product-id"));
        if (!productId) {
            console.warn("No product ID found in cart line");
            return;
        }

        // پیدا کردن line_id از hidden input یا dataset
        const lineId = parseInt($line.data("line-id")) || null;

        // حذف آیتم از کارت

            const result = await rpc("/shop/cart/update_json", {
                product_id: productId,
                line_id: lineId,
                set_qty: 0, // صفر یعنی حذف
                display: true,
            });

            // اگر حذف موفق بود، کارت را رفرش کن
            if (result && result.cart_quantity !== undefined) {

                    window.location.reload();

            }

    },

    _onChangeCartQuantity: function (ev) {
        if($(ev.currentTarget).hasClass('suggested_input')){
            this._super.apply(this, arguments);
        }
        else{
            let $input = $(ev.currentTarget.offsetParent).find('.js_quantity');
            if ($input.data('update_change')) {
                return;
            }
            let value = parseInt($input.val() || 0, 10);
            if (isNaN(value)) {
                value = 1;
            }
            let $dom = $input.closest('.cart_line');
            let $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
            let line_id = parseInt($input.data('line-id'), 10);
            let productIDs = [parseInt($input.data('product-id'), 10)];
            // Applied changes for update/add quantity on cart popover
            if ( $input.val() == 0 && !$input.data('update_change') ){
                $input.data('update_change', true);
                $dom.find('.js_quantity').val(0).trigger('change');
                $dom.remove();
            }
            if (line_id && productIDs){
                this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
                this._onClickFreeShipTextUpdate(ev);
            }
        }
    },
    _onClickRemoveItem: function(ev){
        $(ev.currentTarget).parent().siblings().find('.js_quantity').val(0).trigger('change');
        $(ev.currentTarget).parent().parent().remove();
        this._onClickFreeShipTextUpdate(ev);
    },
    _onClickFreeShipTextUpdate: function(ev){
        setTimeout(function(){
            let $order_total_price = parseFloat($('#order_total .oe_currency_value').text().replace(/[^0-9.]/g, ''));
            let $offer_cart_price = parseFloat($('.offer_price').text().replace(/[^0-9.]/g, ''));
            let result = $order_total_price - $offer_cart_price;
            /*Progress bar design*/
            let progressPercent = Math.min(($order_total_price / $offer_cart_price) * 100, 100);

            if($order_total_price < $offer_cart_price) {
                $('.main_free_ship_data .oe_currency_value').text(Math.abs(result).toFixed(2));
                $('.not_free_ship_text').removeClass('d-none');
                $('.final_msg_ship').addClass('d-none');
                $('.first_main_freeship_price').removeClass('d-none');
                $('.free_ship_not_added').removeClass('d-none');
                $('.progress-fill').css('width', `${progressPercent}%`);
                $('.progress-percentage').text(`${Math.floor(progressPercent)}%`);
            }
            else{
                $('.main_free_ship_data .oe_currency_value').text('0');
                $('.not_free_ship_text').addClass('d-none');
                $('.final_msg_ship').removeClass('d-none');
                $('.first_main_freeship_price').addClass('d-none');
                $('.free_ship_not_added').addClass('d-none');
                $('.progress-fill').css('width', `${progressPercent}%`);
                $('.progress-percentage').text(`${Math.floor(progressPercent)}%`);
            }
        }, 2000);
    },
});
