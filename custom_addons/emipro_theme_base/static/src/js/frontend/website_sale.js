/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

let registry = publicWidget.registry;
let timer;

publicWidget.registry.WebsiteSale.include({
    'selector': '#wrapwrap',
    events: Object.assign({}, publicWidget.registry.WebsiteSale.prototype.events || {}, {
        'click .pricelist_table_row .table_content': '_onClickQty',
    }),
    _onChangeCombination: function(ev, $parent, combination) {
        this._super.apply(this, arguments);

        const current_date = combination.current_date
        const start_date = combination.start_date
        const end_date = combination.end_date
        const msg = combination.offer_msg || ''
        let append_date = '';
        if (end_date != parseInt($(".end_date").val())) {
            if (combination.is_offer && combination.current_date !== 'undefined') {
                append_date = "<div class='timer_input'><input type='hidden' class='current_date' value=" + current_date + "></input><input type='hidden' class='start_date' value=" + start_date + "></input><input type='hidden' class='end_date' value=" + end_date + "></input><div class='te_offer_timer_msg_div'><h6 class='te_offer_timer_prod fw-normal'>" + msg + "</p></h6></div></div>"
                $(".timer_data").html(append_date);
                $(".current_date").trigger('change');
            } else {
                $("#timer_portion_content_ept").removeClass("d-none");
                append_date = "<div class='timer_input'><input type='hidden' class='current_date' value=" + 0 + "></input><input type='hidden' class='start_date' value=" + 0 + "></input><input type='hidden' class='end_date' value=" + 0 + "></input></div>"
                $(".timer_data").html(append_date);
                $(".current_date").trigger('change');
            }
        }
        $(".js_sku_div").html('N/A');
        if (combination.sku_details) {
            $(".js_sku_div").html(combination.sku_details);
        }
        if (combination.price_table_details) {
            $('.te_price_table').removeClass('d-none').html(combination.price_table_details)
        }

        /* Price table selection and qty will be set based on it */
        let getCurrQty = parseInt($('#product_detail .css_quantity .quantity').val());
        if(getCurrQty > 0){
            var finalSelection = this._checkPricelistArr(getCurrQty);
        }
        let blockQty = $(ev.currentTarget).attr('qty');
        if (blockQty){
            $('#product_detail .css_quantity .quantity').html(blockQty);
        }
        if (finalSelection != null){
            $('.table_content').removeClass('active');
            $('.table_content[qty="' + finalSelection + '"]').addClass('active');
        }
    },
    _onClickQty(ev) {
        const $target = $(ev.currentTarget);
        const $qtyInput = this.$(".js_main_product input[name='add_qty']").first();
        $(".table_content").removeClass("active");
        $target.addClass("active");
        const qtyValue = $target.find(".product_qty_span:first").text().trim();
        $qtyInput.val(qtyValue).trigger("change");
    },
    _checkPricelistArr(inputQty){
        const qtyValues = $(".pricelist_table_row .product_qty_span").map((_, el) => parseInt($(el).text().trim(), 10)).get().reverse();
        return qtyValues.find(qty => qty <= inputQty) ?? null;
    },
});

publicWidget.registry.timer_data = publicWidget.Widget.extend({
    selector: ".timer_data",
    events: {
        'change .current_date': 'initOfferTimer',
    },
    start: function() {
        this.redrow();
    },
    stop: function() {
        this.clean();
    },
    redrow: function(debug) {
        this.clean(debug);
        this.build(debug);
    },
    clean: function(debug) {
        this.$target.empty();
    },
    build: function(debug) {},
    initOfferTimer: function() {
        /* This method is called for initialize and update the offer timer in at product page*/
        let product_offer;
        clearInterval(timer);
        let count_start_date = parseInt($(".start_date").val());
        let count_end_date = parseInt($(".end_date").val());
        let current_date_time = parseInt($(".current_date").val());
        $("#timer_portion_content_ept").addClass("d-none");
        timer = setInterval(function() {
            if (count_start_date <= current_date_time && count_end_date >= current_date_time) {
                var duration = count_end_date - current_date_time;
                product_offer = true;
            } else {
                product_offer = false;
            }
            let seconds = "00";
            let days = "00";
            let minutes = "00";
            let hours = "00";
            if (duration > 0) {
                days = Math.floor(duration / (1000 * 60 * 60 * 24));
                hours = Math.floor((duration % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60));
                seconds = Math.floor((duration % (1000 * 60)) / 1000);

                if ((seconds + '').length == 1) {
                    seconds = "0" + seconds;
                }
                if ((days + '').length == 1) {
                    days = "0" + days;
                }
                if ((hours + '').length == 1) {
                    hours = "0" + hours;
                }
                if ((minutes + '').length == 1) {
                    minutes = "0" + minutes;
                }
                if (product_offer == true) {
                    $("#days").text(days);
                    $("#hours").text(hours);
                    $("#minutes").text(minutes);
                    $("#seconds").text(seconds);
                    $(".te_offer_timer_prod").css("display", "block");
                    $("#timer_portion_content_ept").removeClass("d-none");
                }
            }
            current_date_time += 1000
        }, 1000);
    }
});

publicWidget.registry.product_pager = publicWidget.Widget.extend({
    selector: ".next_prev_btn_main",
    events: {
        'mouseenter .product_next_btn, .product_prev_btn': 'getProductInfo',
        'mouseleave .product_next_btn, .product_prev_btn': 'removeProductInfo',
    },
    getProductInfo: function(ev) {
        const windowWidth = $(window).width();
        if (windowWidth > 992) {
            let product_id = $(ev.currentTarget).attr('product-id') || false;
            let params = {'product_id': product_id};
            rpc('/get_product_info', params).then(function (data) {
                $(ev.currentTarget).find('.main_product_container_append').html(data);
            });
        }
    },
    removeProductInfo: function(ev) {
        const windowWidth = $(window).width();
        if (windowWidth > 992) {
            $(ev.currentTarget).find('.main_product_container_append').html('');
        }
    },
});
