/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
let registry = publicWidget.registry;

registry.LoginSigninPopup = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .te_signin': '_te_signin',
        'click #loginRegisterPopup .open_reset_password':'_open_reset_password',
        'click #loginRegisterPopup .back_login': '_back_login',
        'click #loginRegisterPopup .close':'_close',
        'click .validate-sign-in':'_validateSignin',
    },
    _te_signin: function(){
        let loginRegisterPopup = $("#loginRegisterPopup")
        loginRegisterPopup.modal().show().addClass("show modal_shown");
        loginRegisterPopup.find(".oe_reset_password_form").hide();

       loginRegisterPopup.find(".oe_login_form").show();
        $(document).mouseup(function (e) {
            if ($(e.target).closest(".modal-body").length === 0) {
                loginRegisterPopup.removeClass("show modal_shown").hide();
            }
        });
    },
    _open_reset_password:function(){
        let loginRegisterPopup = $("#loginRegisterPopup");
        loginRegisterPopup.find(".oe_login_form").hide();
        loginRegisterPopup.find(".oe_reset_password_form").show();
    },
    _back_login: function(){
        let loginRegisterPopup = $("#loginRegisterPopup");
        loginRegisterPopup.find(".oe_reset_password_form").hide();
        loginRegisterPopup.find(".oe_login_form").show();
    },
    _close: function(){
        $("#loginRegisterPopup").hide();
    },
    _validateSignin: function(e){
        $("#loginRegisterPopup").modal();
        $("#loginRegisterPopup, .modal-body").show();
        $("#loginRegisterPopup").addClass("show modal_shown");
        $("#loginRegisterPopup .oe_reset_password_form").hide();

        let tab = e && $(e.currentTarget).attr('href');
        $('.nav-tabs a[href="' + tab + '"]').tab('show')
        $(document).mouseup(function (e) {
            if ($(e.target).closest(".modal-body").length === 0) {
                $("#loginRegisterPopup").removeClass("show modal_shown").hide();
            }
        });
    },
});

registry.LoginPopup = publicWidget.Widget.extend({
    selector: "#wrapwrap",
    events: {
        'submit #loginRegisterPopup .oe_login_form': '_customerLogin', // on submit of login form from popup
        'submit #loginRegisterPopup .oe_reset_password_form': '_resetPassword' // on submit of reset password form from popup
    },
    _customerLogin: function(e) {
            e.preventDefault()
            let $form = $(e.currentTarget)
            $.ajax({
                url: '/ak/login',
                type: 'POST',
                data: $($form).serialize(),
                async: false,
                success: function(data) {
                    let data_main = JSON.parse(data);
                    let submit_btn = $("#loginRegisterPopup .oe_login_form .te_login_button");
                    let alert_succ_err = $("#loginRegisterPopup .oe_login_form .alert-success-error")
                    if (data_main.login_success && data_main.redirect) {
                        if (data_main.redirect != '1') {
                            if (typeof data_main.hide_msg != 'undefined' && !data_main.hide_msg) {
                                $(alert_succ_err).find(".alert-success").removeClass('d-none');
                            }
                            window.location.replace(data_main.redirect)
                        } else {
                            $(alert_succ_err).find(".alert-success").removeClass('d-none');
                            window.location.reload()
                        }
                    } else if (!data_main.login_success && data_main.error) {
                        $(alert_succ_err).find(".alert-danger").html(data_main.error).removeClass('d-none');
                        $(submit_btn).removeClass('o_website_btn_loading disabled pe-none o_btn_loading').removeAttr('disabled');
                        $("#loginRegisterPopup .oe_login_form .oe_login_buttons .te_login_button .fa-spin").removeClass('fa-refresh fa-spin me-2');
                   }
                },
                error: function(data) {
                    console.log('An error occurred.')
                },
            });
        },

    _customerRegistration: function(e) {
        e.preventDefault()
        let $form = $(e.currentTarget)
        $.ajax({
            url: '/web/signup',
            type: 'POST',
            data: $($form).serialize(),
            async: false,
            success: function(data) {
                let data_main = JSON.parse(data);
                let alert_succ_err = $("#loginRegisterPopup .oe_signup_form .alert-success-error")
                let signup_btn = $("#loginRegisterPopup .oe_signup_form .te_signup_button")
                if (data_main.login_success && data_main.redirect) {
                    $(alert_succ_err).find(".alert-success").removeClass('d-none');
                    window.location.reload()
                } else if (!data_main.login_success && data_main.error) {
                    $(alert_succ_err).find(".alert-danger").html(data_main.error).removeClass('d-none');
                    $(signup_btn).removeAttr('disabled').removeClass('fa-refresh fa-spin pe-none o_btn_loading');
                }
            },
            error: function(data) {
                console.log('An error occurred.')
            },
        });
    },

    _resetPassword: function(e) {
            e.preventDefault()
            let $form = $(e.currentTarget)
            $.ajax({
                url: '/web/reset_password',
                type: 'POST',
                data: $($form).serialize(),
                async: false,
                success: function(data) {
                    let data_main = JSON.parse(data);
                    let alert_succ_err = $("#loginRegisterPopup .oe_reset_password_form .alert-success-error")
                    if (data_main.error) {
                        $(alert_succ_err).html('<p class="alert alert-danger">' + data_main.error + '</p>')
                    } else if (data_main.message) {
                        $(alert_succ_err).html('<p class="alert alert-success">' + data_main.message + '</p>')
                    }
                    setTimeout(function () {
                        $("#loginRegisterPopup").hide();
                    }, 1000);
                },
                error: function(data) {
                    console.log('An error occurred.')
                },
            });
        },
});