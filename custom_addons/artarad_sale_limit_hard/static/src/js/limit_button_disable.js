/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import VariantMixin from "@website_sale/js/sale_variant_mixin";

publicWidget.registry.WebsiteSale.include({

    events: Object.assign({}, publicWidget.registry.WebsiteSale.prototype.events || {}, {
        'keyup form .js_product:first input[name="add_qty"]': '_keyPressQuantity',
        'keyup .oe_cart input.js_quantity[data-product-id]': '_keyPressChangeCartQuantity',
    }),

    _keyPressChangeCartQuantity: function (ev) {
        var $input = $(ev.currentTarget);
        var qty = parseInt($input.val());
        if (isNaN(qty)) {
            qty = 1;
        }
        var max_qty = parseFloat($input.data("limit_max"))
        var $td = $input.closest('td');
        var $error = $td.find('.qty_limit_error')
        var min_qty = parseFloat($(".quantity").data("min"))
        var limit_reached = $(".quantity").data("limit_reached")

        if (limit_reached == "crossed") {
            $error.html(`<div class="text-danger err_msg"><sup>*</sup>Already ordered  maximum quantity!</div>`)
        }

        else if (qty > max_qty) {
            $error.html('<div class="text-danger err_msg"><sup>*</sup>Can\'t order too much quantity!</div>')
            $input.val(max_qty)
            // console.log("_keyPressChangeCartQuantity", qty, max_qty)
        }
        // else if (qty == max_qty) {
        //     $error.html(`<div class="text-danger err_msg"><sup>*</sup>Maximum ordered quantity is ${max_qty}</div>`)
        // }
        // else if (qty == min_qty) {
        //     $error.html(`<div class="text-danger err_msg"><sup>*</sup>Minimum ordered quantity is ${min_qty}</div>`)
        // }
        if (qty < min_qty) {
            $input.val(min_qty)
        }
        // console.log(">>>>>>>>>>>>>>>>>>>>> _keyPressChangeCartQuantity", min_qty)

    },

    _keyPressQuantity: function (ev) {
        // console.log("-----------------------key")
        if ($(".quantity").data("apply_qty_limit") == "True") {
            var qty = parseFloat($(".quantity").val())
            var max_qty = parseFloat($(".quantity").data("limit_max"))
            var min_qty = parseFloat($(".quantity").data("min"))
            var limit_reached = $(".quantity").data("limit_reached")


            if (limit_reached == "crossed") {
                $("#add_to_cart").css({ 'cssText': "display :none !important" })
                $("#add_to_cart_dummy").addClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").removeClass('d-none');
                $("#qty_limit_error").removeClass('d-none')
                $("#qty_limit_error").html(`<div class="text-danger err_msg"><sup>*</sup>Already ordered  maximum quantity!</div>`)
            }


            else if (qty > max_qty) {
                $("#add_to_cart").css({ 'cssText': "display :none !important" })
                $("#add_to_cart_dummy").addClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").removeClass('d-none');
                $("#qty_limit_error").removeClass('d-none')
                $("#qty_limit_error").html('<div class="text-danger err_msg"><sup>*</sup>Can\'t order too much quantity!</div>')

            }
            else if (qty == max_qty) {
                $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
                $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").addClass('d-none');
                $("#max_qty_info").removeClass('d-none')
                $("#min_qty_info").addClass('d-none')
                $("#qty_limit_error").removeClass('d-none')
                $("#qty_limit_error").html(`<div class="text-warning err_msg"><sup>*</sup>Maximum ordered quantity is ${max_qty}</div>`)

            }
            else if (qty > min_qty) {
                $("#qty_limit_error").addClass('d-none')
                $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
                $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").addClass('d-none');
                $("#max_qty_info").addClass('d-none')
                $("#min_qty_info").addClass('d-none')
            }
            else if (qty == min_qty) {
                $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
                $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").addClass('d-none');
                $("#max_qty_info").addClass('d-none')
                $("#min_qty_info").removeClass('d-none')
                $("#qty_limit_error").removeClass('d-none')
//                $("#qty_limit_error").html(`<div class="text-info err_msg"><sup>*</sup>Minimum ordered quantity is ${min_qty}</div>`)

            }
        }
    },

    _onChangeAddQuantity: function (ev) {

        if ($(".quantity").data("apply_qty_limit") == "True") {
            var qty = parseFloat($(".quantity").val())
            var max_qty = parseFloat($(".quantity").data("limit_max"))
            var min_qty = parseFloat($(".quantity").data("min"))
            var limit_reached = $(".quantity").data("limit_reached")

            if (limit_reached == "crossed") {
                $("#add_to_cart").css({ 'cssText': "display :none !important" })
                $("#add_to_cart_dummy").addClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").removeClass('d-none');
                $("#qty_limit_error").removeClass('d-none')
                $("#qty_limit_error").html(`<div class="text-danger err_msg"><sup>*</sup>Already ordered  maximum quantity!</div>`)
            }

            else if (qty > max_qty) {
                $("#add_to_cart").css({ 'cssText': "display :none !important" })
                $("#add_to_cart_dummy").addClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").removeClass('d-none');
                $("#qty_limit_error").removeClass('d-none')

                $("#qty_limit_error").html('<div class="text-danger err_msg"><sup>*</sup>Can\'t order too much quantity!</div>')

            }
            else if (qty == max_qty) {
                $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
                $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").addClass('d-none');
                $("#max_qty_info").removeClass('d-none')
                $("#min_qty_info").addClass('d-none')
                $("#qty_limit_error").removeClass('d-none')
                $("#qty_limit_error").html(`<div class="text-warning err_msg"><sup>*</sup>Maximum ordered quantity is ${max_qty}</div>`)

            }
            else if (qty > min_qty) {
                $("#qty_limit_error").addClass('d-none')
                $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
                $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").addClass('d-none');
                $("#max_qty_info").addClass('d-none')
                $("#min_qty_info").addClass('d-none')
            }
            else if (qty == min_qty) {
                $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
                $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
                $("#add_to_cart_dummy").addClass('d-none');
                $("#max_qty_info").addClass('d-none')
                $("#min_qty_info").removeClass('d-none')
                $("#qty_limit_error").removeClass('d-none')
//                $("#qty_limit_error").html(`<div class="text-info err_msg"><sup>*</sup>Minimum ordered quantity is ${min_qty}</div>`)

            }
        }
        // ************ End *******************************************
        this.onChangeAddQuantity(ev);
    },

    onClickAddCartJSON: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.closest('.input-group').find("input");
        var min = parseFloat($input.data("min") || 0);
        //            var max = parseFloat($input.data("max") || Infinity);
        var stock_max = parseFloat($input.data("max") || Infinity);
        // *************** Extended Code Block **********************
        var limit_max = parseFloat($input.data("limit_max") || Infinity);
        var max = stock_max < limit_max ? stock_max : limit_max
        // ******************** End *********************************
        var previousQty = parseFloat($input.val() || 0, 10);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + previousQty;
        var newQty = quantity > min ? (quantity < max ? quantity : max) : min;

        if (newQty !== previousQty) {
            $input.val(newQty).trigger('change');
        }
        return false;
    },

    _onChangeCartQuantity: function (ev) {
        // console.log("-------------Cart qty")
        var $input = $(ev.currentTarget);
        // ****************** Extended Code Block ********************
        var qty = parseFloat($input.val())
        var max_qty = $input.data("limit_max")
        if (isNaN(max_qty)) {
            if ($input.data('update_change')) {
                return;
            }
            var value = parseInt($input.val() || 0, 10);
            if (isNaN(value)) {
                value = 1;
            }
            var $dom = $input.closest('tr');
            var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
            var line_id = parseInt($input.data('line-id'), 10);
            var productIDs = [parseInt($input.data('product-id'), 10)];
            this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
        }
        else {
            max_qty = parseFloat($input.data("limit_max"))

            if (qty <= max_qty) {
                // var $input = $(ev.currentTarget);
                if ($input.data('update_change')) {
                    return;
                }
                var value = parseInt($input.val() || 0, 10);
                if (isNaN(value)) {
                    value = 1;
                }
                var $dom = $input.closest('tr');
                var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
                var line_id = parseInt($input.data('line-id'), 10);
                var productIDs = [parseInt($input.data('product-id'), 10)];
                this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
            }
        }
    },

    _onChangeCombination: function (ev, $parent, combination) {
        VariantMixin._onChangeCombination.apply(this, arguments);
        // console.log("_onChangeCombination", combination)
        var apply_qty_limit = combination.apply_qty_limit
        if (apply_qty_limit) {
            var limit_min = combination.limit_min
            var limit_max = combination.limit_max
            var limit_reached = combination.limit_reached
            $(".quantity").data("min", limit_min)
            $(".quantity").data("limit_max", limit_max)
            $(".quantity").data("apply_qty_limit", "True")
            var first_set = false
            if ($(".quantity").data("limit_reached") != limit_reached) {
                $(".quantity").data("limit_reached", limit_reached)
                first_set = true
            }


            if ($(".quantity").val() > limit_max || $(".quantity").val() < limit_min || first_set) {
                $(".quantity").val(limit_min).trigger("change")
            }
            this._keyPressQuantity()
        }
        else {
            $(".quantity").data("apply_qty_limit", "False")
            $(".quantity").data("min", "1")
            $(".quantity").data("limit_max", "")
            $("#qty_limit_error").addClass('d-none')
            $("#add_to_cart").css({ 'cssText': "display :inline-block !important" })
            $("#add_to_cart_dummy").removeClass('d-block d-sm-inline-block');
            $("#add_to_cart_dummy").addClass('d-none');
            $("#max_qty_info").addClass('d-none')
            $("#min_qty_info").addClass('d-none')
        }
    },
})
