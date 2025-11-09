/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.dynamicCategoryMegaMenu = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'mouseenter .o_hoverable_dropdown .te_dynamic_ept': '_callScript',
        'click .te_dynamic_ept': '_callScript',
        'mouseenter .o_hoverable_dropdown .te_all_dynamic_ept': '_callFirstEle',
        'click .te_all_dynamic_ept': '_callFirstEle',
    },
    _callFirstEle: function(ev) {
       if ($(window).width() >= 992) {
            const parentCategory = $(ev.currentTarget).find('.menu-categories-container li.nav-item.parent-category');
            const childContent = parentCategory.find('.mobile_cate_child').first();
            const parentElement = childContent.closest('.parent-category');
            parentElement.find('.sub-menu-dropdown').css({"visibility": "visible", "opacity": "1"});
        }
    },
    _callScript: function(ev) {
        $("#custom_menu li").each(function() {
            $(document).on('mouseenter', "#custom_menu_li", function(ev) {
                let li_place = $(this).position().top;
                $(this).children("#custom_recursive").css("top", li_place);
                let self = $(this).children("#custom_recursive");
                if ($(this).children("#custom_recursive").length > 0) {
                    $(self).css({"opacity": "1","visibility": "visible","transform": "translateX(-10px)","transition": "all 0.2s",});
                }
            });
            $(document).on('mouseleave', "#custom_menu_li", function(ev) {
                $(this).children("ul#custom_recursive").css({"opacity": "0","visibility": "hidden","transform": "translateX(20px)",});
            });
        })
    },
});

publicWidget.registry.dynamicCategory = publicWidget.Widget.extend({
    selector: '#top_menu_collapse',
    read_events: {
        'mouseenter .parent-category': '_onMouseEnter',
        'click .mobile_cate_child': '_onMouseEnter',
        'click .sub-menu-dropdown': '_preventClick',
        'click #top_menu .dropdown': '_onClickDynamicMenu',
        'click .ctg_arrow': '_onClickOnArrow',
    },
    _onMouseEnter: function(ev) {
        const windowWidth = $(window).width();
        const self = $(ev.currentTarget);
        const childMenuLength = self.find('.dynamic_mega_menu_child').length;
        const nextElement = $(ev.currentTarget.nextElementSibling);

        if (windowWidth < 992) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        if (childMenuLength !== 1) {
            if (windowWidth > 992) {
                self.find('.sub-menu-dropdown').css({"opacity": "1", "z-index": "99"});
            } else {
                if (nextElement.hasClass('toggle_megamenu')) {
                    nextElement.addClass('no_toggle_megamenu').removeClass('toggle_megamenu');
                } else {
                    self.parents().find('.sub-menu-dropdown').removeClass('toggle_megamenu');
                    self.siblings().addClass('toggle_megamenu').removeClass('no_toggle_megamenu');
                }
            }
        }
    },
    _preventClick: function(ev) {
        ev.stopPropagation();
    },
    _onClickDynamicMenu: function(ev) {
        const self = $(ev.currentTarget);

        if ($(window).width() < 992) {
            const dropdownMenu = self.find(".dropdown-menu");
            const isShown = self.hasClass('show');

            self.toggleClass('show', !isShown);
            dropdownMenu.toggleClass('show', !isShown);
        }
    },
    _onClickOnArrow: function(ev) {
        if ($(window).width() <= 991) {
            const target = $(ev.currentTarget);
            const siblingMenu = target.siblings("ul#custom_recursive");

            target.toggleClass('te_down_ctg_icon');
            ev.preventDefault();

            if (target.hasClass('te_down_ctg_icon')) {
                siblingMenu.slideDown('slow');
            } else {
                siblingMenu.slideUp('slow');
            }
            return false;
        }
    },
});

$(document).ready(function() {
    const header = $('header#top');
    const toggleElements = $('#top_menu').find('.o_mega_menu_toggle');
    const windowWidth = $(window).width();
    if (header.hasClass('o_hoverable_dropdown')) {
        if (windowWidth <= 991) {
            toggleElements.attr('data-bs-toggle', 'dropdown');
        } else {
            toggleElements.removeAttr('data-bs-toggle');
        }
    }
});
