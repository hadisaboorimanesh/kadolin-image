/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

export const Sidebar = publicWidget.Widget.extend({
    template: "theme_clarico_vega.Sidebar",
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        "hidden.bs.offcanvas": "_onHideOffcanvas",
    }),
    init: function (parent, options={}) {
        this._super(parent);
        this._offcanvasInstance = false;
        this.options = options;
        this.lazyLoad = true;
        if ("lazyLoad" in options) {
            this.lazyLoad = options.lazyLoad;
        }
    },
    start: async function () {
        await this._super(...arguments);
        this._appendContent();
    },
    _appendContent: async function () {
        if (this.lazyLoad) {
            await this._getContent().then(content => {
                this.$('.content').replaceWith($(content));
            });
        } else {
            const content = await this._getContent();
            this.$('.content').replaceWith($(content));
        }
    },
    _getContent: function () {
        if (this.options.contentHtml) {
            return Promise.resolve(this.options.contentHtml);
        }
        return $.get(this.options.fetchUrl || "", this.options.fetchParams || {});
    },
    show: function () {
        $("#dynamicOptoffcanvasWithBackdrop .offcanvas-body").empty();
        $(".offcanvas_dynamic_opt #offcanvasWithBackdropLabel").text(_t('Search'));
        return this.appendTo("#dynamicOptoffcanvasWithBackdrop .offcanvas-body").then(() => {
            this._offcanvasInstance = new Offcanvas(this.el);
            return this._offcanvasInstance;
        });
    },
    _onHideOffcanvas: function () {
        this.destroy();
    },
});

export const SearchSidebar = Sidebar.extend({
    _appendContent: async function () {
        await this._super(...arguments);
        this.trigger_up("widgets_start_request", {
            $target: this.$(".o_searchbar_form"),
        });
    },
});

publicWidget.registry.SearchSidebarBtn = publicWidget.Widget.extend({
    selector: ".mobile_header_style",
    read_events: {
        "click .mobile_icon_div .te_search_popover": "async _onClickSearchIcon",
    },
    _onClickSearchIcon: function (ev) {
        ev.preventDefault();
        return new SearchSidebar(this, {
            class: "search-sidebar",
            fetchUrl: "/search_sidebar_ept",
            position: ev.currentTarget.dataset.position || "end",
        }).show();
    },
});