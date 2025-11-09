/** @odoo-modules **/

import { _t } from "@web/core/l10n/translation";
import weSnippetEditor from "@website/js/editor/snippets.editor";
import { patch } from "@web/core/utils/patch";

patch(weSnippetEditor.SnippetsMenu, {
    OptionsTabStructureEpt : [
        ['general-settings-ept', _t("General Settings")],
        ['shop-page-ept', _t("Shop Page")],
        ['product-page-ept', _t("Product Page")],
        ['cart-page-ept', _t("cart Page")],
    ],
    tabs : {
        ...weSnippetEditor.SnippetsMenu.tabs,
        THEME_EPT: 'theme-ept',
    },
    template : "theme_clarico_vega.SnippetsMenu",
});

patch(weSnippetEditor.SnippetsMenu.prototype, {
    setup() {
        super.setup();
    },
    async _onThemeTabClickEpt(ev) {
        let releaseLoader;
        try {
            const promise = new Promise(resolve => releaseLoader = resolve);
            this._execWithLoadingEffect(() => promise, false, 400);
            // loader is added to the DOM synchronously
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            // ensure loader is rendered: first call asks for the (already done) DOM update,
            // second call happens only after rendering the first "updates"
            if (!this.topFakeOptionElEpt) {
                let el;
                for (const [elementName, title] of weSnippetEditor.SnippetsMenu.OptionsTabStructureEpt) {
                    const newEl = document.createElement(elementName);
                    newEl.dataset.name = title;
                    if (el) {
                        el.appendChild(newEl);
                    } else {
                        this.topFakeOptionElEpt = newEl;
                    }
                    el = newEl;
                }
                this.bottomFakeOptionElEpt = el;
                this.el.appendChild(this.topFakeOptionElEpt);
            }

            // Need all of this in that order so that:
            // - the element is visible and can be enabled and the onFocus method is
            //   called each time.
            // - the element is hidden afterwards so it does not take space in the
            //   DOM, same as the overlay which may make a scrollbar appear.
            this.bottomFakeOptionElEpt.classList.remove('d-none');
            const editorPromise = this._activateSnippet($(this.bottomFakeOptionElEpt));
            // Because _activateSnippet uses the same mutex as the loader
            releaseLoader();
            releaseLoader = undefined;
            this.bottomFakeOptionElEpt.classList.add('d-none');
            this._updateRightPanelContent({
                tab: weSnippetEditor.SnippetsMenu.tabs.THEME_EPT,
            });
        } catch (e) {
            // Normally the loading effect is removed in case of error during the action but here
            // the actual activity is happening outside of the action, the effect must therefore
            // be cleared in case of error as well
            if (releaseLoader) {
                releaseLoader();
            }
            throw e;
        }
    },
});
