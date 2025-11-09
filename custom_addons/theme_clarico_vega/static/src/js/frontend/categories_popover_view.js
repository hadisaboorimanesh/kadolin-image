/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
let registry = publicWidget.registry;

registry.CategoriesListPopoverView = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .te_categories_list_popover': '_initCategoriesListPopoverView',
        'click .te-parent-category span.fa': '_clickToShowChildCategories',
    },

    _initCategoriesListPopoverView: async function (ev) {
        ev.preventDefault();
        $("#dynamicOptoffcanvasWithBackdrop .offcanvas-body").empty();
        await rpc('/get_categories_list_data').then(function (data) {
           $(".offcanvas_dynamic_opt #offcanvasWithBackdropLabel").text(_t('Categories'));
           $("#dynamicOptoffcanvasWithBackdrop .offcanvas-body").html(data);
        });
    },

    _clickToShowChildCategories: function (ev) {
        ev.preventDefault();
        const currFaId = ev.currentTarget.id;
        const currChildCategory = $(`#te_child_category_${currFaId}`);
        $(".te_child_category").not(currChildCategory).slideUp();
        currChildCategory.stop(true, true).slideToggle(500);
        $(".spn_arrow").not(ev.currentTarget).removeClass('fa-angle-down').addClass('fa-angle-right');
        $(ev.currentTarget).toggleClass('fa-angle-right fa-angle-down');
    },
});