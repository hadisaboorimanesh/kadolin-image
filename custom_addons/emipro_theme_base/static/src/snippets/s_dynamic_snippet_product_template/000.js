/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";
import DynamicSnippetProducts from "@website_sale/snippets/s_dynamic_snippet_products/000";
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.dynamic_snippet_products.include({
    _getBrandSearchDomain() {
        const searchDomain = [];
        let productBrandIds = this.$el.get(0).dataset.productBrandIds;
        if (productBrandIds && productBrandIds !== 'all') {
            if (productBrandIds && productBrandIds != '[]') {
                searchDomain.push(['product_brand_id', 'in', JSON.parse(productBrandIds).map(productBrand => productBrand.id)]);
            }
        }
        return searchDomain;
    },
    getSelectedProductTemplateSearchDomain() {
        const searchDomain = [];
        let productTemplateIds = this.$el.get(0).dataset.productTemplateIds;
        let productBrandIds = this.$el.get(0).dataset.productBrandIds;
        if (productTemplateIds && productTemplateIds != '[]') {
            if (productBrandIds && productBrandIds != '[]') {
                searchDomain.push('|',['id', 'in', JSON.parse(productTemplateIds).map(productTemplate => productTemplate.id)]);
            } else {
                searchDomain.push(['id', 'in', JSON.parse(productTemplateIds).map(productTemplate => productTemplate.id)]);
            }
        }
        return searchDomain;
    },
    _getSearchDomain: function () {
        const searchDomain = this._super.apply(this, arguments);
        searchDomain.push(...this.getSelectedProductTemplateSearchDomain());
        searchDomain.push(...this._getBrandSearchDomain());
        return searchDomain;
    },
    async _fetchData() {
        if (this._isConfigComplete()) {
            const nodeData = this.el.dataset;
            const data = {
                'add2cart': this.$el.attr('data-add2cart'),
                'wishlist': this.$el.attr('data-wishlist'),
                'compare': this.$el.attr('data-compare'),
                'quickview': this.$el.attr('data-quickview'),
                'rating': this.$el.attr('data-rating'),
                'product_label': this.$el.attr('data-product_label'),
                'color_swatches': this.$el.attr('data-color_swatches'),
                'image_flipper': this.$el.attr('data-image_flipper'),
            };
            const filterFragments = await rpc(
                '/website/snippet/filters',
                Object.assign({
                    'filter_id': parseInt(nodeData.filterId),
                    'template_key': nodeData.templateKey,
                    'limit': parseInt(nodeData.numberOfRecords),
                    'search_domain': this._getSearchDomain(),
                    'with_sample': this.editableMode,
                    'product_context': data,
                }, this._getRpcParameters(),
                    JSON.parse(this.el.dataset?.customTemplateData || "{}"))
            );
            this.data = filterFragments.map(markup);
        } else {
            this.data = [];
        }
    },
    _getQWebRenderOptions: function () {
        return Object.assign(
            this._super.apply(this, arguments),
            {
                gridMode: this.el.dataset.gridMode || 1,
            },
        );
    },
});
