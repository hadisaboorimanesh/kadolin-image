/** @odoo-module */
const signupForm = document.querySelector('.oe_signup_form, .oe_reset_password_form');
if (signupForm) {

    var $sms_btn = $('#button_get_verification_code_by_SMS');
    $sms_btn.click(function () {
        if (!$("#mobile").val() || $("#mobile").val().length != 11 || $("#mobile").val().substring(0, 2) != "09") {
            $("#mobile").focus();
        } else {
            // Send sms for mobile
            $.post("/authsignupsendsms", {
                mobile: $("#mobile").val()
            });

            // Disable 'Get verification code by SMS' button for 60 seconds to prevent user form continuous clicking
            // Display a 60 seconds countdown in button string
            $sms_btn.attr('disabled', 'disabled');
            var seconds = 60;
            var countdown = setInterval(function () {
                seconds--;
                $sms_btn.text('Get verification code by SMS (' + seconds + ')');
                if (seconds <= 0) {
                    clearInterval(countdown);
                    $sms_btn.removeAttr("disabled");
                    $sms_btn.text('Get verification code by SMS');
                }
            }, 1000);
        }
    });
}