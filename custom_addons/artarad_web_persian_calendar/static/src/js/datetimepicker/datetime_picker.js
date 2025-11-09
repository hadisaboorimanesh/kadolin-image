/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { isInRange, today } from "@web/core/l10n/dates";

const { Info } = luxon;

/**
* @property {WeekItem[]} weeks
* @typedef WeekItem
 */

const toDateItem = ({ isOutOfRange = false, isValid = true, label, range, extraClass }) => ({
    id: range[0].toISODate(),
    includesToday: isInRange(today(), range),
    isOutOfRange,
    isValid,
    label: String(range[0]["j" + label]),
    range,
    extraClass,
});

const toWeekItem = (weekDayItems) => ({
    number: weekDayItems[3].range[0].jweekNumber,
    days: weekDayItems,
});

const getStartOfWeek = (date) => {
    const { weekStart } = localization;
    return date.set({ weekday: date.weekday < weekStart ? weekStart - 7 : weekStart });
};

const numberRange = (min, max) => [...Array(max - min)].map((_, i) => i + min);

const getStartOfDecade = (date) => Math.floor(date.jyear / 10) * 10;

const getStartOfCentury = (date) => Math.floor(date.jyear / 100) * 100;

const GRID_COUNT = 10;
const GRID_MARGIN = 1;
const DAYS_PER_WEEK = 7;
const WEEKS_PER_MONTH = 6;

const PRECISION_LEVELS = new Map()
    .set("days", {
        mainTitle: _t("Select month"),
        nextTitle: _t("Next month"),
        prevTitle: _t("Previous month"),
        step: { jmonth: 1 },
        getTitle: (date, { additionalMonth }) => {
            const titles = [`${date.jmonthLong} ${date.jyear}`];
            if (additionalMonth) {
                const next = date.plus({ jmonth: 1 });
                titles.push(`${next.jmonthLong} ${next.jyear}`);
            }
            return titles;
        },
        getItems: (
            date,
            { additionalMonth, maxDate, minDate, showWeekNumbers, isDateValid, dayCellClass }
        ) => {
            const startDates = [date];
            if (additionalMonth) {
                startDates.push(date.plus({ jmonth: 1 }));
            }

            /** @type {WeekItem[]} */
            const lastWeeks = [];
            let shouldAddLastWeek = false;

            const dayItems = startDates.map((date, i) => {
                const monthRange = [date.startOf("jmonth"), date.endOf("jmonth")];
                /** @type {WeekItem[]} */
                const weeks = [];

                // Generate 6 weeks for current month
                let startOfNextWeek = getStartOfWeek(monthRange[0]);
                for (let w = 0; w < 6; w++) {
                    const weekDayItems = [];
                    // Generate all days of the week
                    for (let d = 0; d < 7; d++) {
                        const day = startOfNextWeek.plus({ day: d });
                        const range = [day, day.endOf("day")];
                        const dayItem = toDateItem({
                            isOutOfRange: !isInRange(day, monthRange),
                            isValid: isInRange(range, [minDate, maxDate]) && isDateValid?.(day),
                            label: "day",
                            range,
                            extraClass: dayCellClass?.(day) || "",
                        });
                        weekDayItems.push(dayItem);
                        if (d === DAYS_PER_WEEK - 1) {
                            startOfNextWeek = day.plus({ day: 1 });
                        }
                        if (w === WEEKS_PER_MONTH - 1) {
                            shouldAddLastWeek ||= !dayItem.isOutOfRange;
                        }
                    }
                    const weekItem = toWeekItem(weekDayItems);
                    if (w === WEEKS_PER_MONTH - 1) {
                        lastWeeks.push(weekItem);
                    } else {
                        weeks.push(weekItem);
                    }
                }

                // Generate days of week labels
                const daysOfWeek = weeks[0].days.map((d) => [
                    d.range[0].weekdayShort,
                    d.range[0].weekdayLong,
                    Info.weekdays("narrow", { locale: d.range[0].locale })[d.range[0].weekday - 1],
                ]);
                if (showWeekNumbers) {
                    daysOfWeek.unshift(["#", _t("Week numbers"), "#"]);
                }

                return {
                    id: `__month__${i}`,
                    number: monthRange[0].jmonth,
                    daysOfWeek,
                    weeks,
                };
            });

            if (shouldAddLastWeek) {
                // Add last empty week item if the other month has an extra week
                for (let i = 0; i < dayItems.length; i++) {
                    dayItems[i].weeks.push(lastWeeks[i]);
                }
            }

            return dayItems;
        },
    })
    .set("months", {
        mainTitle: _t("Select year"),
        nextTitle: _t("Next year"),
        prevTitle: _t("Previous year"),
        step: { jyear: 1 },
        getTitle: (date) => String(date.jyear) ,
        getItems: (date, { maxDate, minDate }) => {
            const startOfYear = date.startOf("jyear");
            return numberRange(0, 12).map((i) => {
                const startOfMonth = startOfYear.plus({ jmonth: i });
                const range = [startOfMonth, startOfMonth.endOf("jmonth")];
                return toDateItem({
                    isValid: isInRange(range, [minDate, maxDate]),
                    label: "monthShort",
                    range,
                });
            });
        },
    })
    .set("years", {
        mainTitle: _t("Select decade"),
        nextTitle: _t("Next decade"),
        prevTitle: _t("Previous decade"),
        step: { jyear: 10 },
        getTitle: (date) => `${getStartOfDecade(date) - 1} - ${getStartOfDecade(date) + 10}`,
        getItems: (date, { maxDate, minDate }) => {
            const startOfDecade = date.startOf("jyear").set({ jyear: getStartOfDecade(date) });
            return numberRange(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
                const startOfYear = startOfDecade.plus({ jyear: i });
                const range = [startOfYear, startOfYear.endOf("jyear")];
                return toDateItem({
                    isOutOfRange: i < 0 || i >= GRID_COUNT,
                    isValid: isInRange(range, [minDate, maxDate]),
                    label: "year",
                    range,
                });
            });
        },
    })
    .set("decades", {
        mainTitle: _t("Select century"),
        nextTitle: _t("Next century"),
        prevTitle: _t("Previous century"),
        step: { jyear: 100 },
        getTitle: (date) => `${getStartOfCentury(date) - 10} - ${getStartOfCentury(date) + 100}`,
        getItems: (date, { maxDate, minDate }) => {
            const startOfCentury = date.startOf("jyear").set({ jyear: getStartOfCentury(date) });
            return numberRange(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
                const startOfDecade = startOfCentury.plus({ jyear: i * 10 });
                const range = [startOfDecade, startOfDecade.plus({ jyear: 10, millisecond: -1 })];
                return toDateItem({
                    label: "year",
                    isOutOfRange: i < 0 || i >= GRID_COUNT,
                    isValid: isInRange(range, [minDate, maxDate]),
                    range,
                });
            });
        },
    });

if(odoo.user_calendar_type === "jalaali") {
    DateTimePicker.props.maxPrecision = {
        type: [...PRECISION_LEVELS.keys()].map((value) => ({ value })),
        optional: true,
    };

    DateTimePicker.props.minPrecision = {
        type: [...PRECISION_LEVELS.keys()].map((value) => ({ value })),
        optional: true,
    };

    DateTimePicker.defaultProps.daysOfWeekFormat = "narrow";
}

patch(DateTimePicker.prototype, {
    get activePrecisionLevel() {
        if(odoo.user_calendar_type === "jalaali") {
            return PRECISION_LEVELS.get(this.state.precision);
        }
        return super.activePrecisionLevel;
    },

    filterPrecisionLevels(minPrecision, maxPrecision) {
        if(odoo.user_calendar_type === "jalaali") {
            const levels = [...PRECISION_LEVELS.keys()];
            return levels.slice(levels.indexOf(minPrecision), levels.indexOf(maxPrecision) + 1);
        }
        return super.filterPrecisionLevels(minPrecision, maxPrecision);
    },

    adjustFocus(values, focusedDateIndex) {
        if(odoo.user_calendar_type === "jalaali") {
            if (!this.shouldAdjustFocusDate && this.state.focusDate) {
                return;
            }

            let dateToFocus =
                values[focusedDateIndex] || values[focusedDateIndex === 1 ? 0 : 1] || today();

            if (
                this.additionalMonth &&
                focusedDateIndex === 1 &&
                values[0] &&
                values[1] &&
                values[0].jmonth !== values[1].jmonth
            ) {
                dateToFocus = dateToFocus.minus({ jmonth: 1 });
            }

            this.shouldAdjustFocusDate = false;
            this.state.focusDate = this.clamp(dateToFocus.startOf("jmonth"));
        }
        else {
            super.adjustFocus(values, focusedDateIndex);
        }
    },
    
});