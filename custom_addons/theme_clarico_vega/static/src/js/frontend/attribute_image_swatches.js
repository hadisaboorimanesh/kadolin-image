/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.AttributeColorPane = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'mouseenter .oe_product_image_img_wrapper': '_onMouseEnterFlip',
        'mouseleave .oe_product_image_img_wrapper': '_onMouseLeaveSwatch',
        'mouseenter .attribute_color': '_onMouseEnterSwatch',
        'mouseleave .attribute_color': '_onMouseLeaveSwatch',
    }),
    _onMouseEnterFlip: function(ev) {
        const $target = $(ev.currentTarget);
        let second_image = $target.find('img').attr('hover-image');
        if(second_image){
            if(second_image.trim() != '/web/image/product.image/product.image()/image_512' && second_image.trim() != '/web/image/product.image/product.image()/image_1920'){
                $target.find('img').attr('src', second_image);
            }
        }
    },
    _onMouseLeaveSwatch: function(ev) {
        let target = $(ev.currentTarget).find('img').attr('data-original') || $(ev.currentTarget).attr('data-original');
        $(ev.currentTarget).find('img').attr('src', target);
        $(ev.currentTarget).parents('.o_wsale_product_grid_wrapper, .o_carousel_product_card').find('.oe_product_image img, .o_img_product_cover').attr('src', target);
    },
    _onMouseEnterSwatch: async function(ev) {
        const $target = $(ev.currentTarget);
        let data = $target.data();
        let params = {
            'value_id': data.attributeValueId,
            'product_id': data.productId
        }
        let url;
        await rpc('/hover/color', params).then((data) => {
            url = data && data.url;
        });
        url && $target.parents('.o_wsale_product_grid_wrapper, .o_carousel_product_card').find('.oe_product_image img, .o_img_product_cover').attr('src', url);
    },
});
