/** @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToFragment } from "@web/core/utils/render";
const { DateTime } = luxon;

function getLang() {
    var html = document.documentElement;
    return (html.getAttribute('lang') || 'en_US').replace('-', '_');
}

publicWidget.registry.appointmentSlotSelect.include({
    _onClickDaySlot: function (ev) {
        this.$('.o_slot_selected').removeClass('o_slot_selected active');
        this.$(ev.currentTarget).addClass('o_slot_selected active');

        const slotDate = this.$(ev.currentTarget).data('slotDate');
        const slots = this.$(ev.currentTarget).data('availableSlots');
        const scheduleBasedOn = this.$("input[name='schedule_based_on']").val();
        const resourceAssignMethod = this.$("input[name='assign_method']").val();
        const resourceId = this.$("input[name='resource_selected_id']").val();
        const resourceCapacity = this.$("select[name='resourceCapacity']").val();
        let commonUrlParams = new URLSearchParams(window.location.search);
        // If for instance the chosen slot is already taken, then an error is thrown and the
        // user is brought back to the calendar view. In order to keep the selected user, the
        // url will contain the previously selected staff_user_id (-> preselected in the dropdown
        // if there is one). If one changes the staff_user in the dropdown, we do not want the
        // previous one to interfere, hence we delete it. The one linked to the slot is used.
        // The same is true for duration and date_time used in form rendering.
        commonUrlParams.delete('staff_user_id');
        commonUrlParams.delete('resource_selected_id');
        commonUrlParams.delete('duration');
        commonUrlParams.delete('date_time');
        if (resourceCapacity) {
            commonUrlParams.set('asked_capacity', encodeURIComponent(resourceCapacity));
        }
        if (resourceId) {
            commonUrlParams.set('resource_selected_id', encodeURIComponent(resourceId));
        }

        this.$slotsList.empty().append(renderToFragment('appointment.slots_list', {
            commonUrlParams: commonUrlParams,
            resourceAssignMethod: resourceAssignMethod,
            scheduleBasedOn: scheduleBasedOn,
            slotDate: getLang() === 'fa_IR' ? '\u202B' + DateTime.fromISO(slotDate).toFormat("jcccc jdd jMMMM jyyyy") + '\u202C' : DateTime.fromISO(slotDate).toFormat("cccc dd MMMM yyyy"),
            slots: slots,
            getAvailableResources: (slot) => {
                return scheduleBasedOn === 'resources' ? JSON.stringify(slot['available_resources']) : false;
            }
        }));
        this.$resourceSelection.addClass('d-none');
    },

});
