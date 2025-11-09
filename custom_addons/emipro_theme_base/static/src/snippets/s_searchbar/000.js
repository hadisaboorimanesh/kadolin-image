/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { renderToElement, renderToString } from "@web/core/utils/render";

publicWidget.registry.searchBar.include({
    _render: function(res) {
        if (this._scrollingParentEl) {
            this._scrollingParentEl.removeEventListener('scroll', this._menuScrollAndResizeHandler);
            window.removeEventListener('resize', this._menuScrollAndResizeHandler);
            delete this._scrollingParentEl;
            delete this._menuScrollAndResizeHandler;
        }

        let pageScrollHeight = null;
        const $prevMenu = this.$menu;
        if (res && this.limit) {
            const results = res['results'];
            const categories = res['categories'];
            const quickLink = res['is_quick_link'];
            let template = 'website.s_searchbar.autocomplete';
            const candidate = template + '.' + this.searchType;
            if (candidate in renderToString.app.rawTemplates) {
                template = candidate;
            }
            this.$menu = $(renderToElement(template, {
                results: results,
                categories: categories,
                quickLink: quickLink,
                parts: res['parts'],
                hasMoreResults: results.length < res['results_count'],
                search: this.$input.val(),
                fuzzySearch: res['fuzzy_search'],
                widget: this,
            }));
            this.$menu.css('min-width', this.autocompleteMinWidth);

            // Handle the case where the searchbar is in a mega menu by making
            // it position:fixed and forcing its size. Note: this could be the
            // default behavior or at least needed in more cases than the mega
            // menu only (all scrolling parents). But as a stable fix, it was
            // easier to fix that case only as a first step, especially since
            // this cannot generically work on all scrolling parent.
            const megaMenuEl = this.el.closest('.o_mega_menu');
            if (megaMenuEl) {
                const navbarEl = this.el.closest('.navbar');
                const navbarTogglerEl = navbarEl ? navbarEl.querySelector('.navbar-toggler') : null;
                if (navbarTogglerEl && navbarTogglerEl.clientWidth < 1) {
                    this._scrollingParentEl = megaMenuEl;
                    this._menuScrollAndResizeHandler = () => this._adaptToScrollingParent();
                    this._scrollingParentEl.addEventListener('scroll', this._menuScrollAndResizeHandler);
                    window.addEventListener('resize', this._menuScrollAndResizeHandler);

                    this._adaptToScrollingParent();
                }
            }

            pageScrollHeight = document.documentElement.scrollHeight;
            this.$el.append(this.$menu);

            this.$el.find('button.extra_link').on('click', function(event) {
                event.preventDefault();
                window.location.href = event.currentTarget.dataset['target'];
            });
            this.$el.find('.s_searchbar_fuzzy_submit').on('click', (event) => {
                event.preventDefault();
                this.$input.val(res['fuzzy_search']);
                const form = this.$('.o_search_order_by').parents('form');
                form.submit();
            });
        }

        this.$el.toggleClass('dropdown show', !!res);
        if ($prevMenu) {
            $prevMenu.remove();
        }

        // Adjust the menu's position based on the scroll height.
        if (res && this.limit) {
            this.el.classList.remove("dropup");
            delete this.$menu[0].dataset.bsPopper;
            if (document.documentElement.scrollHeight > pageScrollHeight) {
                // If the menu overflows below the page, we reduce its height.
                this.$menu[0].style.maxHeight = "40vh";
                this.$menu[0].style.overflowY = "auto";
                // We then recheck if the menu still overflows below the page.
                if (document.documentElement.scrollHeight > pageScrollHeight) {
                    // If the menu still overflows below the page after its height
                    // has been reduced, we position it above the input.
                    this.el.classList.add("dropup");
                    this.$menu[0].dataset.bsPopper = "";
                }
            }
        }
    },
});
