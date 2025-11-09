
/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {DynamicSnippet} from '@website/snippets/s_dynamic_snippet/000';
import animations from "@website/js/content/snippets.animation";
import OwlMixin from "@theme_clarico_vega/js/frontend/mixins";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

let registry = publicWidget.registry;
let dynamic_snippet = registry.dynamic_snippet;

registry.Lazyload = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    start() {
        if ($('#id_lazyload').length) {
            $("img.lazyload").lazyload();
        }
        this._super(...arguments);
    },
});

/* function for manage live chat button */
function chatBtn(btnHeight, cookie_height) {
    if (cookie_height) {
        $('.openerp.o_livechat_button').css({ 'bottom': cookie_height + 'px' });
    } else {
        $('.openerp.o_livechat_button').css({ 'bottom': '0px' });
    }
}

/* Sticky product details */
//function for manage sticky add to cart with live chat button
function stickyMobileDevice(fixIconHeaderStyle, btnHeight, cookie_height) {
    let pwa_bar = $('.ios-prompt').height();
    setTimeout(function() {
        if ($('.ios-prompt').is(':visible')) {
            btnHeight = (pwa_bar + btnHeight + 30);
            cookie_height = (pwa_bar + cookie_height + 30);
        }
    }, 8000);
    if( $(fixIconHeaderStyle).length ){
        $('.mobile_header_style').css({'bottom': btnHeight +'px'});
        $('div#wrapwrap .product_details_sticky').css({'display':'block', 'position':'fixed', 'top':'initial'});
        $('.openerp.o_livechat_button').css({'bottom': (fixIconHeaderStyle + btnHeight) +'px'});
    } else {
        $('div#wrapwrap .product_details_sticky').css({ 'display': 'block', 'position': 'fixed', 'bottom': cookie_height + 'px', 'top': 'initial' });
        $('.openerp.o_livechat_button').css({ 'bottom': btnHeight + 'px' });
    }
}

animations.registry.mobileHeaderStyle = animations.Animation.extend({
    selector: '#wrapwrap',
    effects: [{
        startEvents: 'scroll',
        update: '_stickyMobileHeader',
    }],
    _stickyMobileHeader: function(scroll) {
       if ($(window).width() < 992) {
           if(scroll + $(window).height() == $(document).height()) {
               $('.mobile_header_style').fadeOut();
           }
           else {
               $('.mobile_header_style').fadeIn();
           }
       }
    }
});

animations.registry.StickyGallery = animations.Animation.extend({
    selector: '#wrapwrap',
    effects: [{
        startEvents: 'scroll',
        update: '_stickyDetails',
    }],
    _stickyDetails: function(scroll) {
        // Sticky add to cart bar
        if ($('.product_details_sticky').length) {
            if ($('div#product_details a#add_to_cart').length) {
                let getPriceHtml = $('div#product_details .product_price').html();
                let btnHeight = $('div#wrapwrap .product_details_sticky').height();
                let cookie_height = 0;
                if ($('.o_cookies_discrete .s_popup_size_full').length) {
                    cookie_height = $('.s_popup_size_full .modal-content').height()
                }
                let footerPosition = $("main").height() - $("#footer").height();
                let fixIconHeaderStyle = $('.mobile_header_style').height() + 15;
                let productDetails = $('#product_details').height() - $('#o_product_terms_and_share').height();
                if (scroll > productDetails && scroll < footerPosition - 500) {
                    if ($(window).width() >= 768) {
                        $('div#wrapwrap .product_details_sticky').css('bottom', cookie_height + 'px').fadeIn();
                        $('.o_product_feature_panel').css({'bottom': fixIconHeaderStyle + $('.product_details_sticky').height()}).fadeIn();
                    }
                    /* Display prices on add to cart sticky*/
                    if ($(".js_product.js_main_product").hasClass("css_not_available")) {
                        $('div#wrapwrap .prod_price').html('');
                    } else {
                        $('div#wrapwrap .prod_price').html(getPriceHtml);
                    }
                    /* Ipad view only */
                    if ($(window).width() >= 768 && $(window).width() <= 991) {
                        stickyMobileDevice(fixIconHeaderStyle, btnHeight, cookie_height);
                    }
                } else {
                    if ($(window).width() >= 768) {
                        $('.o_product_feature_panel').css({'bottom':0});
                        $('div#wrapwrap .product_details_sticky').css('bottom', cookie_height + 'px').fadeOut();
                    }
                    if ($(window).width() >= 768 && $(window).width() <= 991) {
                        chatBtn(btnHeight, cookie_height);
                    }
                }
                /* Mobile view sticky add to cart */
                if ($(window).width() <= 767) {
                    let relativeBtn = $('main').height() + $('header').height();
                    let pwaStickyHeight = $('.mobile_header_style').outerHeight();
                    let productStickyHeight = $('.product_details_sticky').outerHeight();
                    if(scroll < relativeBtn){
                        $('#add_to_cart_wrap .js_check_product, .o_we_buy_now').css('display','none');
                        stickyMobileDevice(fixIconHeaderStyle, btnHeight, cookie_height);
                        $('.ios-prompt').css({'margin-bottom': '0', 'bottom': productStickyHeight});
                        if($('.mobile_header_style').length) {
                            $('.ios-prompt').css('bottom', $('.mobile_header_style').outerHeight());
                            if($('.product_details_sticky').length){
                                $('.ios-prompt').css({'bottom': pwaStickyHeight+productStickyHeight});
                            }
                        }
                        if($('.o_cookies_discrete').length != 0){
                             $('.o_cookies_discrete .s_popup_size_full .oe_structure').css({'bottom':$('.product_details_sticky').height()});
                        }
                    } else {
                        $('div#wrapwrap .product_details_sticky').fadeOut();
                        $('.mobile_header_style').css({'bottom': '15px'});

                         if($('.ios-prompt') && $('.mobile_header_style').length == 0){
                            $('.ios-prompt').css('bottom', 0)
                         }
                         else{
                            $('.ios-prompt').css('bottom', pwaStickyHeight);
                            $('.mobile_header_style').css('bottom', '15px');
                         }
                        $('.o_cookies_discrete .s_popup_size_full .oe_structure').css({'bottom':0});
                        chatBtn(btnHeight, cookie_height);
                    }
                }
            }
        }
    },
});

/* Mobile Sidebar Menu */
publicWidget.registry.responsiveMobileHeader = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .header_sidebar': '_headerSidebar',
        'click .close_top_menu': '_closeLeftHeader',
    },
    init: function() {
        this._super(...arguments);
        this.header_height = 0;
        if ($('.o_main_navbar').length) {
            this.header_height = $('.o_main_navbar').height();
        }
    },
    _headerSidebar: function() {
        $("#top_menu_collapse").addClass("header_menu_slide").css('top', this.header_height).show('slow');
        $("#top_menu_collapse").animate({
            width: '100%'
        });
        $("#wrapwrap").addClass("wrapwrap_trans_header");
        $(".te_mega_menu_ept a.dropdown-toggle.o_mega_menu_toggle").attr('href', '#');
        $(".parent-category .mobile_cate_child").attr('href', '#');
    },
    _closeLeftHeader: function() {
        $("#top_menu_collapse").animate({
            width: '0'
        });
        $("#wrapwrap").removeClass("wrapwrap_trans_header");
    }
});

/* Header Mobile Search Icon Toggle */
publicWidget.registry.themeSearch = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .te_srch_icon': '_onSearchClickOpen',
        'click .te_srch_close': '_onSearchClickClose',
        'click .te_srch_icon_5': '_onSearch5ClickOpen',
        'click .te_srch_close_5': '_onSearch5ClickClose',
        'keyup input[name="search"]': '_onSearchClickData',
        'click .te_srch_close_ept': '_onSearchCloseEpt',
    },
    start: function() {
        this._onSearchClickData();
        /*Add code for mega menu style 9 mobile view*/
        $("#custom_menu_ept li").each(function() {
            let has_ctg = $(this).find("ul.t_custom_subctg").length > 0;
            if (has_ctg) {
                $(this).append("<a class='ctg_arrow float-end fa fa-angle-right py-2' />")
                $(this).click(function(ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    if($(ev.target).hasClass('categ_ept')){
                        window.location.replace($(ev.target).attr('href'))
                        return
                    }
                    let self = $(this).find("ul.t_custom_subctg")[0];
                    if(!$(ev.target).find('ul').length && !$(ev.target).hasClass('ctg_arrow')) {
                        if($(ev.target).find('a').attr('href')){
                            window.location.replace($(ev.target).find('a').attr('href'))
                        }
                        return
                    }
                    $(self).stop().animate({
                        width: "100%"
                    });
                    $(self).css({
                        "display": "block",
                        "transition": "0.3s easeout",
                        "z-index": 99
                    })
                    $(self).parent(".t_custom_subctg").css("overflow-y", "hidden");
                    $(self).parent(".t_custom_subctg").scrollTop(0);
                    $(this).parents("#custom_menu_ept").scrollTop(0);
                    $(this).parents("#custom_menu_ept").css("overflow-y", "hidden");
                });
                $(this).find("ul.t_custom_subctg").children(".te_prent_ctg_heading").click(function(ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    $(this).parent("ul#custom_recursive_ept").stop().animate({
                        width: "0"
                    }, function() {
                        $(this).css("display", "none")
                        $(this).parent().parent(".t_custom_subctg").css("overflow-y", "auto");
                    });
                });
            }
        });
        $("#custom_menu_ept > li > ul.t_custom_subctg > .te_prent_ctg_heading").click(function() {
            $(this).parents("#custom_menu_ept").css("overflow-y", "auto");
        });
        let containerHeight = $('header').height();
        $('.search_bar_right5').css('height', containerHeight+ 'px');
    },
    _onSearchClickOpen: function(ev) {
        const searchbarInput = $('.o_searchbar_form input[name="search"]');
        const isRightHeaderStyle = $('.te_header_style_right').length;
        const isPopupSearchForm = $(".te_searchform__popup").length;
        setTimeout(() => searchbarInput.focus(), 500);

        if (isRightHeaderStyle) {
            $(".te_search_popover").addClass("visible");
            $(ev.currentTarget).hide();
            $(".te_srch_close").css('display', 'block');
        } else if (isPopupSearchForm) {
            $(".te_searchform__popup").addClass("open");
            $(".te_srch_close").show();
        }
    },
    _onSearchClickClose: function(ev) {
        const isRightHeaderStyle = $('.te_header_style_right').length;
        const isPopupSearchForm = $(".te_searchform__popup").length;

        if (isRightHeaderStyle) {
            $(".te_search_popover").removeClass("visible");
            $(ev.currentTarget).not('.te_srch_close_5').hide();
            $(".te_srch_icon").show();
        } else if (isPopupSearchForm) {
            $(".te_searchform__popup").removeClass("open");
            $(".te_srch_icon").show();
        }
    },
    _onSearch5ClickOpen: function(ev) {
        const searchbarInput = $('.o_searchbar_form input[name="search"]');
        const isRightHeaderStyle = $('.te_header_style_right').length;
        const isPopupSearchForm = $(".te_searchform__popup").length;
        setTimeout(() => searchbarInput.focus(), 500);

        if (isRightHeaderStyle) {
            $(".te_search_popover").addClass("visible");
            $('.te_header_style_right').slideDown(250);
            $(".te_srch_close").css('display', 'block');
        } else if (isPopupSearchForm) {
            $(".te_searchform__popup").addClass("open");
            $(".te_srch_close").show();
        }
    },
    _onSearch5ClickClose: function(ev) {
        const isRightHeaderStyle = $('.te_header_style_right').length;
        const isPopupSearchForm = $(".te_searchform__popup").length;

        if (isRightHeaderStyle) {
            $(".te_search_popover").removeClass("visible");
            $('.te_header_style_right').slideUp(250);
            $(".te_srch_icon_5").show();
        } else if (isPopupSearchForm) {
            $(".te_searchform__popup").removeClass("open");
            $(".te_srch_icon_5").show();
        }
    },
    _onSearchClickData: function() {
        let input_val = $('input[name="search"]').val();
        if (input_val) {
            $('.te_srch_close_ept').css("display", "block");
        }
    },
   _onSearchCloseEpt: function() {
        const searchParams = new URLSearchParams(window.location.search);
        const isSearchBodyPresent = !!$('.te_searchform__body, .te_sub_search').length;
        const searchInput = $('input[name="search"]');
        const searchCloseButton = $('.te_srch_close_ept');

        searchInput.val('');
        if (isSearchBodyPresent) {
            searchCloseButton.hide();
        } else if (searchParams.has('search')) {
            $('button[type="submit"]').trigger('click');
        } else {
            searchCloseButton.hide();
            $(".search_btn_close").trigger('click');
        }
   },

});

registry.brandPage = publicWidget.Widget.extend(OwlMixin, {
    selector: ".featured-all-brands",
    read_events: {
        'click .has-brands': '_onClickAlpha',
        'click #all-brands': '_showAllBrands',
        'keyup #search_box': '_onKeyupInput'
    },
    _onClickAlpha: function(ev) {
        this.showAllBrands();
        let $this = $(ev.currentTarget);
        let value = $('#search_box').val();
        $this.children().toggleClass('selected');
        let selected_letter_arr = []
        $('.selected').each(function(i) {
            selected_letter_arr.push($.trim($(this).text()))
        });
        if ($.inArray("0-9", selected_letter_arr) != -1){
            selected_letter_arr.push('1', '2', '3', '4', '5', '6', '7', '8', '9');
        }
        $('.brand-alpha-main').each(function(e) {
            let first_letter = $(this).find('.brand-name').attr('brand_name').substring(0, 1).toLowerCase();
            if ($.inArray(first_letter, selected_letter_arr) == -1 && selected_letter_arr.length != 0) {
                $(this).addClass('d-none');
            }
        });
        if (value) {
            this.removeBlocks(value);
        }
    },
    _showAllBrands: function(ev) {
        $('.selected').removeClass('selected');
        this.showAllBrands();
        let value = $('#search_box').val();
        this.removeBlocks(value);
    },
    _onKeyupInput: function(ev) {
        $('.selected').removeClass('selected');
        let value = $(ev.currentTarget).val();
        this.showAllBrands();
        this.enableBrandBox();
        if (value.length >= 1) {
            this.removeBlocks(value);
            this.disableBox(value);
        }
    },
    showAllBrands: function() {
        $('.brand-alpha-main').each(function(e) {
            $(this).find('.brand-item.d-none').each(function(e) {
                $(this).removeClass('d-none');
            });
            $(this).removeClass('d-none');
        });
    },
    removeBlocks: function(value) {
        $('.brand-alpha-main').each(function(i) {
            let flag = 0
            $(this).find('.brand-item').each(function(i) {
                let brand = $(this).find('.brand-name').attr('brand_name')
                if (brand.toLowerCase().indexOf(value.toLowerCase()) == -1) {
                    $(this).addClass('d-none');
                }
                if (!$(this).hasClass('d-none')) {
                    flag = 1;
                }
            });
            if (flag == 0) {
                $(this).addClass('d-none');
            }
        });
    },
    enableBrandBox: function() {
        $('.has-brands.active').each(function(i) {
            if ($(this).hasClass('disabled')) {
                $(this).removeClass('disabled');
            }
        });
    },
    disableBox: function(value) {
        let enabled_array = new Array();
        $('.brand-alpha-main').each(function(i) {
            let flag = 0;
            $(this).find('.brand-item').each(function(i) {
                if (flag == 0) {
                    let brand = $(this).find('.brand-name').attr('brand_name');
                    if (brand.toLowerCase().indexOf(value.toLowerCase()) != -1) {
                        enabled_array.push($(this).find('.brand-name').attr('brand_name').substring(0, 1).toLowerCase());
                        flag = 1;
                    }
                } else {
                    return false;
                }
            });
        });
        if (enabled_array.length == 0) {
            $('.has-brands.active').each(function(i) {
                $(this).addClass('disabled');
            });
        } else {
            enabled_array.forEach(function(item) {
                $('.has-brands.active').each(function(i) {
                    if ($.inArray($.trim($(this).children('.brand-alpha').text()), enabled_array) == -1) {
                        $(this).addClass('disabled');
                    }
                });
            });
        }
    }
});
/* Update top position value on live chat button  */
patch(LivechatButton.prototype, {
    setup() {
        super.setup();
        let headerHeight = $('.mobile_header_style').height() || false;
        let stickyHeight = $('.product_details_sticky').height() || false;
        let pwaBarHeight = $('.ios-prompt').is(':visible') ? $('.ios-prompt').height() : false;
        if ($('.mobile_header_style').length){
             let totalHeights = "calc(97% - (" + (headerHeight + stickyHeight + pwaBarHeight + 54) +
              "px))";
             this.position.top = totalHeights;
        }
    },
});

dynamic_snippet && dynamic_snippet.include({
    _renderContent: function () {
        this._super(...arguments);

        $('.s_product_brand_style_3 .dynamic-owl-carousel').each(function(index){
            let responsive = { 0: {items: 2}, 576: {items: 3}, 991: {items: 1}, 1200: {items: 1} };
            OwlMixin.initOwlCarousel('.s_product_brand_style_3 .dynamic-owl-carousel', 15, responsive, true, 1, false, true, false, false, false, false, true, false);
        });
        const $templateArea = this.$el.find('.dynamic_snippet_template');
        this._super(...arguments);
        if ($templateArea.find('img.lazyload')){
            $("img.lazyload").lazyload();
        }

        let interval = parseInt(this.$target[0].dataset.carouselInterval);
        let mobile_element_count = this.$target[0].dataset.numberOfElementsSmallDevices;
        $('.dynamic-owl-carousel:not(.product_builder_banner .dynamic-owl-carousel, .dynamic_columns_snippet .dynamic-owl-carousel,.brand_builder_banner .dynamic-owl-carousel)').each(function(index) {
            var owl_rtl = false;
            if ($('#wrapwrap').hasClass('o_rtl')) {
                owl_rtl = true;
            }
            var $items = $(this);
            var item = $items.attr('data-slide-size') || 1;
            var slider_len = $items.find(".item").length == 0 ? $items.find(".card").length : $items.find(".item").length;
            var getItemLength = slider_len > 4 ? true : false;
            var dots = $items.parents('.dynamic_columns_snippet').length ? true : false;
            var autoplay = true;
            if(slider_len > item){
                getItemLength = true;
            }
            if($items.parents('.product_slider_style9')){
                autoplay = false;
            }
            $items.owlCarousel({
                loop: getItemLength,
                margin: 15,
                nav: true,
                navText : ['<i class="fa fa-angle-left"></i>','<i class="fa fa-angle-right"></i>'],
                autoplay: autoplay,
                autoplayTimeout: interval,
                autoplayHoverPause:true,
                items: item,
                dots: dots,
                rtl: owl_rtl,
                responsive: {
                    0: { items: mobile_element_count == undefined ? 1.5 : parseInt(mobile_element_count) + 0.5},
                    576: { items: item > 1 ? 2.5 : parseInt(item) + 0.5 },
                    991: { items: item > 1 ? item - 0.5 : parseInt(item) + 0.5 },
                    1200: { items: parseInt(item) + 0.5 },
                },
            });
            if( $items.find('.owl-nav').hasClass('disabled')){
                if(slider_len > item){
                    $items.find('.owl-nav').show();
                }
            }
            if($items.parents('.s_product_template_style_4')){
                $items.find('.owl-dots').show();
            }
        });
        $('.product_builder_banner .dynamic-owl-carousel, .dynamic_columns_snippet .dynamic-owl-carousel,.brand_builder_banner .dynamic-owl-carousel, .dynamic-owl-carousel').each(function(index) {
            var owl_rtl = false;
            if ($('#wrapwrap').hasClass('o_rtl')) {
                owl_rtl = true;
            }
            var $items = $(this);
            var item = $items.attr('data-slide-size') || 1;
            var slider_len = $items.find(".item").length == 0 ? $items.find(".card").length : $items.find(".item").length;
            var getItemLength = slider_len > 4 ? true : false;
            var dots = $items.parents('.dynamic_columns_snippet').length ? true : false;
            var autoplay = true;
            if(slider_len > item){
                getItemLength = true;
            }
            if($items.parents('.product_slider_style9')){
                autoplay = false;
            }
            $items.owlCarousel({
                loop: getItemLength,
                margin: 15,
                nav: true,
                navText : ['<i class="fa fa-angle-left"></i>','<i class="fa fa-angle-right"></i>'],
                autoplay: autoplay,
                autoplayTimeout: interval,
                autoplayHoverPause:true,
                items: item,
                dots: dots,
                rtl: owl_rtl,
                responsive: {
                    0: { items: mobile_element_count == undefined ? 1 : parseInt(mobile_element_count)},
                    576: { items: item > 1 ? 2 : item },
                    991: { items: item > 1 ? item - 1 : item },
                    1200: { items: item },
                },
            });
            if( $items.find('.owl-nav').hasClass('disabled')){
                if(slider_len > item){
                    $items.find('.owl-nav').show();
                }
            }
            if($items.parents('.s_product_template_style_4')){
                $items.find('.owl-dots').show();
            }
        });
        $("img.lazyload").lazyload();
    },
});

registry.SeeAllProcess = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    read_events: {
        'click .see_all_attr_btn': '_get_see_all_data',
        'click div.te_s_attr_color': '_filter_color_attribute_click',
    },
    _get_see_all_data: function(ev) {
        const $target = $(ev.currentTarget);
        let attr_id = $target.attr('attr-id');
        let is_mobile = $target.attr('is-mobile');
        let is_tag = $target.attr('is-tag');
        let is_brand = $target.attr('is-brand');
        let attr_count = $('input[type="hidden"][name="attr_count"]').val();
        let brand_count = $('input[type="hidden"][name="brand_count"]').val();
        let tag_count = $('input[type="hidden"][name="tag_count"]').val();

        let params = {'attr_id': attr_id, 'is_mobile': is_mobile, 'attr_count': attr_count, 'brand_count': brand_count, 'is_brand': is_brand, 'tag_count': tag_count, 'is_tag': is_tag};

        rpc('/see_all', params).then(function (data) {
            if(is_tag == 'True'){
                $('.tags_filter').html(data);
            }

            if(is_brand == 'True'){
                if(is_mobile == 'True'){
                    $('#o_wsale_offcanvas_attribute_0').html(data);
                }
                else{
                    $('#o_products_attributes_brand').html(data);
                }
                $('.see_all_attr_0').hide()
            }
            else{
                if(is_mobile == 'True'){
                    $('#o_wsale_offcanvas_attribute_'+attr_id).html(data);
                }
                else{
                    $('#o_products_attributes_'+attr_id).html(data);
                }
                $('.see_all_attr_'+attr_id).hide()
            }
        });
    },

    /*======= color attribute click=========== */
    _filter_color_attribute_click: function(ev){
        $(ev.target).find('.css_attribute_color').trigger('click');
        if(ev.target.classList.contains('te_color-name')){
            $(ev.target).prev().trigger('click');
        }
    },
});

registry.SearchOnBrandFilter = publicWidget.Widget.extend({
    selector: '.oe_website_sale, #o_wsale_offcanvas_content',
    read_events: {
        'click .o_products_attributes_brand, .o_products_attributes_all': '_onBrandAttribSection',
        'keyup .js_attrib_search_ept, .js_attrib_search_all_ept': '_onKeyupAttribSearch',
    },
    _onBrandAttribSection: async function(ev) {
        let searchElement = $(ev.currentTarget).parents('.accordion-item').find("#js_attrib_search");
        if ($(ev.currentTarget).hasClass('collapsed')){
            searchElement.addClass('d-none').removeClass('d-block');
        } else{
            searchElement.removeClass('d-none').addClass('d-block');
        }
    },
    _onKeyupAttribSearch: function(ev) {
        ev.preventDefault();
        let parent = $(ev.currentTarget).parents('.accordion-item');
        parent.find('#js_attrib_search').find('.no_found_msg').remove()
        let key = $(ev.currentTarget).val().toUpperCase()
        if ( $(window).width() <= 767 && $('#o_wsale_offcanvas_content').length ){
            parent.find('.form-check, .te_s_attr_color').each(function(){
                let labelVal = $(this).find('label').attr('title') == undefined ? $(this).find('label').text() : $(this).find('label').attr('title');
                if (labelVal && labelVal.toUpperCase().indexOf(key) > -1) {
                    $(this).closest("div.list-group-item, .te_s_attr_color, div.form-check").removeClass('d-none');
                } else {
                    $(this).closest("div.list-group-item, .te_s_attr_color, div.form-check").addClass('d-none');
                }
            });
        } else {
            parent.find('label.form-check-label:not(.lbl_see_all)').each(function(){
                if ($(this).text().toUpperCase().indexOf(key) > -1) {
                    $(this).closest("div.form-check, div.te_s_attr_color, div.list-group-item").removeClass('d-none');
                } else {
                    $(this).closest("div.form-check, div.te_s_attr_color, div.list-group-item").addClass('d-none');
                }
            });
        }

        if (parent.find('div.form-check, div.te_s_attr_color').not('.d-none').length == 0) {
            parent.find('.js_attrib_search, .js_attrib_search_all').after('<div class="no_found_msg m-3 alert alert-danger">No result found ... </div>')
        }
    },
});

 /* Attribute value tooltip */
$(function() {
    $('[data-bs-toggle="tooltip"]').tooltip({animation: true,delay: {show: 300,hide: 100} })

    /* Brands owl Slider for Mega Menu Style 1 */
    $('.te_menu_brand_img').each(function(index){
        let responsive = { 0: {items: 2}, 576: {items: 3}, 991: {items: 4}, 1200: {items: 4} };
        OwlMixin.initOwlCarousel('.te_menu_brand_img', 10, responsive, true, 1, false, false, true, true, false, false, true, false);
    });

});

/*=== ScrollReview =====*/
registry.ScrollReview = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .ept-total-review': 'scroll_review_tab',
    },
    scroll_review_tab: function() {
        if ($(window).width() >= 993) {
            if ($("#nav_tabs_link_ratings").length > 0) {
                let header_height = 10;
                if ($('header#top').length && !$('header').hasClass('o_header_sidebar')) {
                    if ($('header nav').hasClass('te_header_navbar')) {
                        this.header_height = $('header nav').height() + 30;
                    } else {
                        this.header_height = $('header').height() + 30;
                    }
                }
                let totalHeight = parseInt($("#nav-tab").offset().top) - parseInt(header_height) - parseInt($("#nav-tab").outerHeight());
                if ($(window).width() < 768)
                    totalHeight += 120;
                $([document.documentElement, document.body]).animate({
                    scrollTop: totalHeight
                }, 2000);
                $('#nav_tabs_link_ratings').trigger('click');
            }
        }
        if ($(window).width() <= 992) {
            if ($("#collapse_ratings").length > 0) {
                let header_height = 10;
                if ($('header#top').length && !$('header').hasClass('o_header_sidebar')) {
                    if ($('header nav').hasClass('te_header_navbar')) {
                        this.header_height = $('header nav').height() + 20;
                    } else {
                        this.header_height = $('header').height() + 20;
                    }
                }
                let totalHeight = parseInt($("#prd-tab-content").offset().top) - parseInt(header_height) - parseInt($("#prd-tab-content").outerHeight());
                if ($(window).width() < 768)
                    totalHeight += 120;
                $([document.documentElement, document.body]).animate({
                    scrollTop: totalHeight
                }, 2000);
                $('#collapse_ratings').trigger('click');
                $("#collapse_ratings").addClass("show");
            }
        }
    }
});

registry.productTabs = publicWidget.Widget.extend({
    selector: '.product_tabs_ept',
    start: function () {
        // Optimised code due to old js code.
        const desktopTabs = document.querySelectorAll('#nav-tab button');
        const mobileTabs = document.querySelectorAll('#prd-tab-content .tab-pane');

        desktopTabs.forEach((btn, i) => {
            const desktopTabId = btn.id;
            const mobileTabId = mobileTabs[i]?.id;

            if (!desktopTabId || !mobileTabId) return;

            const desktopSpans = document.querySelectorAll(`#${desktopTabId} a > span`);
            const mobileSpans = document.querySelectorAll(`#${mobileTabId} a > span`);

            if (!desktopSpans.length || !mobileSpans.length) return;

            if (desktopSpans[0].classList.contains('fa')) {
                // Case: FontAwesome icon + text
                const iconClass = desktopSpans[0].className;
                const textVal = desktopSpans[1]?.innerText?.trim();

                if (mobileSpans[0]) mobileSpans[0].className = iconClass;
                if (mobileSpans[1] && textVal) mobileSpans[1].innerText = textVal;
            } else {
                // Case: nested span for icon
                const nestedIcon = document.querySelector(`#${desktopTabId} a > span span`)?.className;
                if (nestedIcon && mobileSpans[0]) {
                    mobileSpans[0].className = nestedIcon;
                }
            }
        });
    }
});

publicWidget.registry.ProductWishlist.include({
    'selector': '#wrapwrap',
});
publicWidget.registry.ProductComparison.include({
    'selector': '#wrapwrap',
});
/*hotspot setting for display basic product card and advance product card*/
var timeout;
publicWidget.registry.displayHotspot = publicWidget.Widget.extend({
    selector: ".hotspot_element.display_card",
    events: {
        'mouseenter': '_onMouseEnter',
        'mouseleave': '_onMouseLeave',
    },

    start: function () {
        this.$el.popover({
            trigger: 'manual',
            animation: true,
            html: true,
            container: 'body',
            placement: 'auto',
            sanitize: false,
            template: '<div class="popover hotspot-popover" role="tooltip"><div class="tooltip-arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>'
        });
        return this._super(...arguments);
    },

    _onMouseEnter: function (ev) {
        let self = this;
        self.hovered = true;
        clearTimeout(timeout);
        $(this.selector).not(ev.currentTarget).popover('hide');
        timeout = setTimeout(function () {
            /*Render the Hotspot Product detail popover template*/
            self._popoverRPC = $.get("/get-pop-up-product-details", {
                'product': parseInt($(ev.currentTarget).attr("data-product-template-ids")),
            }).then(function (data) {
                var WebsiteSale = new publicWidget.registry.WebsiteSale();
                const popover = Popover.getInstance(self.$el[0]);
                popover._config.content = data;
                popover.setContent(popover._getTipElement());
                self.$el.popover("show");
                $('.popover').on('mouseleave', function () {
                    self.$el.trigger('mouseleave');
                });
                $(".hotspot-popover .a-submit").off('click').on('click',function(ev) {
                    ev.preventDefault();
                    var $form = $(ev.currentTarget).closest('form')
                    WebsiteSale._handleAdd($form);
                });
            });
        }, 300);
    },

    _onMouseLeave: function (ev) {
        let self = this;
        self.hovered = false;
        setTimeout(function () {
            if ($('.popover:hover').length) {
                return;
            }
            if (!self.$el.is(':hover')) {
               self.$el.popover('hide');
            }
        }, 1000);
    },
});

publicWidget.registry.offerOffcanvasAnimation = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    start: function() {
        /* offer off-canvas animation */
        let main_offer = $('.offer_sidebar_offcanvas_button');
        main_offer.css('top', $('#top').height());

        const toggleButton = $('.offer_sidebar_btn');
        const offcanvasElement = $('#custom_offer_popup_button');

        offcanvasElement.on('show.bs.offcanvas', function () {
            $(main_offer).css("transition", "0.3s ease");
            $(main_offer).css("right", "25rem");
            toggleButton.addClass('open');
        });
        offcanvasElement.on('hide.bs.offcanvas', function () {
            $(main_offer).css("transition", "0.3s ease");
            $(main_offer).css("right", "0");
            toggleButton.removeClass('open');
        });
    },
});


// The cursor moves to the top of the content instead of the next element when the enter key is pressed.[FIXED]
$(document).ready(function () {
    $(document).on('keydown', '#product_full_description.o_editable', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.execCommand('insertLineBreak');
            const sel = window.getSelection();
            if (sel.anchorNode) {
                $(sel.anchorNode.parentElement).get(0).scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }
    });
});
