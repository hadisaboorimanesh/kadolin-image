/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import ProductWishlist from '@website_sale_wishlist/js/website_sale_wishlist'; // Path to the original module
//import { jsonrpc } from "@web/core/network/rpc_service";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.ProductWishlist.include({

    /**
     * Inherit the `_onClickAddWish` method to show popup of collections
     * @private
     * @param {Event} ev
     */
    _onClickAddWish: function (ev) {
        $('#wishlist_toast').toast("show");
        $('#wishlist_toast .add_to_collection').attr('data-product-id',$(ev.currentTarget).attr('data-product-product-id'));
        this._super.apply(this, arguments);  // super call
    },

    /**
     * Overrode the `_removeWish` method to manage the wishlist count
     * @private
     */
    _removeWish: async function (e, deferred_redirect) {
        let tr = $(e.currentTarget).parents('tr');
        let wish = tr.data('wish-id');
        let product = tr.data('product-id');
        let self = this;

        rpc('/shop/wishlist/remove/' + wish).then(function () {
            $(tr).hide();
        });

        let totalWishlistProductIDs = this.wishlistProductIDs
        await rpc('/shop/wishlist/all_products', {}).then(function (data) {
            totalWishlistProductIDs = JSON.parse(data);
        });

        this.wishlistProductIDs = totalWishlistProductIDs.filter((p) => p !== product);
        sessionStorage.setItem('website_sale_wishlist_product_ids', JSON.stringify(this.wishlistProductIDs));
        if (this.wishlistProductIDs.length === 0) {
            if (deferred_redirect) {
                deferred_redirect.then(function () {
                    self._redirectNoWish();
                });
            }
        }
        this._updateWishlistView();
    },
});

publicWidget.registry.collection = publicWidget.Widget.extend({
    selector: "#wrapwrap",
    events: {
        'input .collection_name': 'checkCollName',
        'click .btn_select_coll': 'addToCollection',
        'change input:radio[name=coll_radio_box]': 'onChangeCollection',
        'click .btn_product_add_to_cart': 'addToCartProduct',
        'click .btn_coll_remove': 'removeColl',
        'click .btn_product_remove': 'removeProduct',
        'click .btn_coll_share': 'shareColl',
        'click .btn_create_collection': 'createCollection',
        'click #btn_collection_create': 'collectionCreate',
        'click .add_to_collection': '_displayCollectionPopup',
        'click .btn_coll_rename': 'renameColl',
        'click #coll_rename_btn': 'renameCollection'
    },

    renameCollection : function(ev){
        ev.preventDefault()
        let collection_id = $('#rnm_collection_id').val();
        let collection_name = $(".wishlist_rename_collection_body").find('input[name="collection_name"]').val();
        if(collection_name !== undefined && collection_name.trim() !== '' && collection_id !== undefined){
            rpc('/rename_collection', {'collection_name':collection_name, 'collection_id':collection_id}).then(function(response) {
                window.location.reload();
            });
        }
    },

    renameColl: function(ev) {
        ev.preventDefault()
        let element = ev.currentTarget;
        let collection_id = $(element).attr('data-id');

        $("#collection_rename_modal").modal('show');
        $("#rnm_collection_id").val(collection_id);
        $('#coll_rename_btn').attr('data-id', collection_id);
    },

    /**
     * Display a popup to add product in collection.
     * @private
     */
    _displayCollectionPopup: async function (ev) {
        let product_qty = 1;
        let _quantity = $(".quantity");
        if (_quantity[0] === undefined || _quantity[0] === null) {
            product_qty = _quantity[0].value;
        }
        let modalDiv = $("#select_collection_modal")
        await rpc('/select_collection_modal_data', {}).then((data) => {
            modalDiv.html(data);
        });
        let modal_body = modalDiv.find('.modal-body');
        modal_body.find(".product_qty")[0].value = product_qty;
        this._checkCollections(ev, product_qty);
    },
    _selectCollection: function(ev, collections) {
        let $el = $(ev.currentTarget)
        let productID = $el.data('product-product-id');
        let modalDiv = $("#select_collection_popup")
        modalDiv.modal('show');
        let modal_body = modalDiv.find('.modal-body');
        modal_body[0].firstElementChild.value = productID;
        let collection_id = $(".colls input[type='radio']:checked").attr('data-id');
        if(collection_id){
            $('.btn_select_coll').removeAttr('disabled');
        }
    },
    _checkCollections: function(ev, product_qty=1) {
        let self = this;
        rpc('/check_collections', {}).then(function(response) {
            if(response['is_partner']){
                self._selectCollection(ev, response['collections']);
            }
        });
    },

    collectionCreate: function(ev){
        let collection_name = $(".create_collection_body").find('input[name="collection_name"]').val();
        if(collection_name !== undefined && collection_name !== ''){
            rpc('/add_select_collection', {'collection_name':collection_name}).then(function(response) {
                window.location.reload();
            });
        }
    },

    createCollection: function(ev){
        $("#collection_create_modal").modal('show');
    },

    _sendColl: function(ev, collection_id) {
        ev.preventDefault();
        let recipient_email = $('#recipient_email').val();
        let regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;

        $(".wishlist_collection_msg").html("");

        if(regex.test(recipient_email)){
            rpc('/send_collection', {'collection_id':collection_id, 'recipient_email': recipient_email}).then(function(response) {
                if(response){
                    $('#recipient_email').val('');
                    $(".wishlist_collection_msg").html("");
                    $(".wishlist_collection_msg").html("<p class='label label-success'>Shared Successfully!</p>");
                }
            });
        }
        else{
            $(".wishlist_collection_msg").html("Invalid email address!");
        }
    },

    shareColl: function(ev) {
        let self = this
        ev.preventDefault()
        let element = ev.currentTarget;
        let collection_id = $(element).attr('data-id');

        $(".wishlist_collection_msg").html("");
        $("#collection_share_modal").modal('show');

        $('#btn_coll_send').on('click', function() {
            self._sendColl(ev, collection_id);
        });
    },

    _isProductExist: function(ev, collection_id, product_id) {
        ev.preventDefault()
        $(".collection_creation").find(".collection_name")[0].value = '';
        $('.collection_name_message').addClass('d-none');
        rpc('/check_product_in_collection', {'collection_id':collection_id, 'product_id':product_id}).then(function(response) {
            if(response){
                $('.product_exist_message').removeClass('d-none');
                $('.btn_select_coll').attr({'disabled':'True'});
            }else{
                $('.btn_select_coll').removeAttr('disabled');
                $('.product_exist_message').addClass('d-none');
            }
        });
    },

    onChangeCollection: function(ev){
        let self = this
        let collection_id = $(".colls input[type='radio']:checked").attr('data-id');
        let modal_body = $("#select_collection_popup").find('.modal-body');
        let product_id = modal_body[0].firstElementChild.value;
        self._isProductExist(ev, collection_id, product_id);
    },

    checkCollName: function(ev){
        /* This method is called when user typing name in input box of add new collection
         and will inform user about entered name is valid or not */
         ev.preventDefault()
         let collection_name = $('.collection_name')[0].value;
         rpc('/check_collection_name', {'collection_name':collection_name}).then(function(response) {
            if(response){
                $('.btn_coll_add').removeAttr('disabled');
                $('.collection_name_message').addClass('d-none');
                $('.btn_select_coll').removeAttr('disabled');
            }else{
                $('.btn_coll_add').attr({'disabled':'True'});
                $('.collection_name_message').removeClass('d-none');
                $('.btn_select_coll').attr({'disabled':'True'});
            }
         });
    },

    addProductToCollection: function(collection_id, product_id, product_qty){
        // Add product in collection
        rpc('/add_product_in_collection', {'collection_id':collection_id, 'product_id':product_id, 'product_qty':product_qty}).then(function(response) {
            if(!response){
                $('.product_exist_message').removeClass('d-none');
            }
        });
    },

    addToCollection: function(ev){
        /* This method is called when user click on the `Add to Collection` button of popup
         and add the products in the collection */
        let self = this
        let collection_id = $(".colls input[type='radio']:checked").attr('data-id');
        let modal_body = $("#select_collection_popup").find('.modal-body')
        let productID = parseInt($('#wishlist_toast .add_to_collection').attr('data-product-id'));
        let product_qty = modal_body.find(".product_qty")[0].value;
        if(collection_id){
            self.addProductToCollection(collection_id, productID, product_qty);
        }else if (!collection_id){
            let collection_name = $(".collection_creation").find(".collection_name")[0].value;
            rpc('/add_select_collection', {'collection_name':collection_name}).then(function(response) {
                collection_id = response
                self.addProductToCollection(collection_id, productID, product_qty);
            });
        }
    },

    addToCartProduct: function(ev) {
        /* This method is called while click on the Add to Cart(Product) button
         and will add clicked product into cart */
        ev.preventDefault()
        let self = this;
        let element = ev.currentTarget;
        let product_line_id = $(element).attr('data-id');
        rpc('/add_to_cart_collection', {'product_line_id': product_line_id}).then(function(response) {
            // Remove product from collection once added to the cart based on the b2b_wish checkbox
            if (!$('#b2b_wish').is(':checked')) {
                self.removeProduct(ev);
            }
            window.location.href = '/shop/cart';
        });
    },

    removeColl: function(ev) {
        /* This method is called while click on the Remove(Collection) button
         and will remove that collection if user confirms it*/
        ev.preventDefault()
        let self = this;
        let element = ev.currentTarget;
        let collection_id = $(element).attr('data-id');
        rpc('/check_collection', {'collection_id':collection_id}).then(function(response) {
            if(response){
                $("#collection_delete_modal").modal('show'); // Open the modal
                $('.yes').on('click', function() {
                    self.delCollection(element, collection_id);
                });
                $("#collection_delete_modal").modal('hide'); // Close the modal
            }else{
                self.delCollection(element, collection_id);
            }
        });
    },

    delCollection: function(element, collection_id){
        let self = this;
        //  Delete Collection
        rpc('/remove_collection', {'collection_id':collection_id}).then(function(response) {
            if(!response){
                alert("You can delete only your lists!");
            }
            let collectionRec = $(element).closest('div.collection_rec')
            let collectionID = collectionRec.data('collection_id');
            let collectionProductLines = $('div.whole_product_line[data-ref_collection_id="' + collectionID + '"]');


            let removedProducts = collectionProductLines.length;

            collectionProductLines.hide();
            collectionRec.hide();

            self._updateWishlistLength(removedProducts);
        });
    },

    removeProduct: function(ev) {
        /* This method is called while click on the Remove(Product) button
         and will remove that product from collection */
        ev.preventDefault()
        let self = this;
        let element = ev.currentTarget;
        let product_line_id = $(element).attr('data-id');
        rpc('/remove_product', {'product_line_id':product_line_id}).then(function(response) {
            $(element).closest('div.wishlist_collection_tbody').hide();
            self._updateWishlistLength(1);
        });
    },

    _updateWishlistLength: async function(noOfProduct){
        let $wishButton = $('.te_header_right_icon .o_wsale_my_wish');
        if(!$wishButton || $wishButton.length == 0){
            $wishButton = $('.o_wsale_my_wish');
        }
        let $wishQuantityElement = $wishButton.find('.my_wish_quantity');

        let totalProductsCount = '[]'
        await rpc('/shop/wishlist/all_products', {}).then(function (data) {
            totalProductsCount = data;
        });

        // Set new quantity in session storage as well so that the default flow not conflicts with custom flow
        sessionStorage.setItem('website_sale_wishlist_product_ids', totalProductsCount);

        let newProductCount = JSON.parse(totalProductsCount).length;
        // Set the new total number of products back into the element
        $wishQuantityElement.text(newProductCount);

    },
});
