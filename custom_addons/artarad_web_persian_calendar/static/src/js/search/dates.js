/** @odoo-module **/
import * as search_dates from "@web/search/utils/dates";
import { QUARTERS } from "@web/search/utils/dates";

import { _lt } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { clamp } from "@web/core/utils/numbers";
import { pick } from "@web/core/utils/objects";

const jQUARTER_OPTIONS = {
    fourth_quarter: {
        id: "fourth_quarter",
        groupNumber: 1,
        description: QUARTERS[4].description,
        setParam: { jquarter: 4 },
        granularity: "jquarter",
    },
    third_quarter: {
        id: "third_quarter",
        groupNumber: 1,
        description: QUARTERS[3].description,
        setParam: { jquarter: 3 },
        granularity: "jquarter",
    },
    second_quarter: {
        id: "second_quarter",
        groupNumber: 1,
        description: QUARTERS[2].description,
        setParam: { jquarter: 2 },
        granularity: "jquarter",
    },
    first_quarter: {
        id: "first_quarter",
        groupNumber: 1,
        description: QUARTERS[1].description,
        setParam: { jquarter: 1 },
        granularity: "jquarter",
    },
};

function jgetMonthPeriodOptions(referenceMoment, optionsParams) {
    const { startYear, endYear, startMonth, endMonth } = optionsParams;
    return [...Array(endMonth - startMonth + 1).keys()]
        .map((i) => {
            const monthOffset = startMonth + i;
            const date = referenceMoment.plus({
                jmonths: monthOffset,
                jyears: clamp(0, startYear, endYear),
            });
            const yearOffset = date.jyear - referenceMoment.jyear;
            return {
                id: search_dates.toGeneratorId("month", monthOffset),
                defaultYearId: search_dates.toGeneratorId("year", clamp(yearOffset, startYear, endYear)),
                description: date.toFormat("jMMMM"),
                granularity: "jmonth",
                groupNumber: 1,
                plusParam: { jmonths: monthOffset },
            };
        })
        .reverse();
}

function jgetQuarterPeriodOptions(optionsParams) {
    const { startYear, endYear } = optionsParams;
    const defaultYearId = search_dates.toGeneratorId("year", clamp(0, startYear, endYear));
    return Object.values(jQUARTER_OPTIONS).map((quarter) => ({
        ...quarter,
        defaultYearId,
    }));
}

function jgetYearPeriodOptions(referenceMoment, optionsParams) {
    const { startYear, endYear } = optionsParams;
    return [...Array(endYear - startYear + 1).keys()]
        .map((i) => {
            const offset = startYear + i;
            const date = referenceMoment.plus({ jyears: offset });
            return {
                id: search_dates.toGeneratorId("year", offset),
                description: date.toFormat("jyyyy"),
                granularity: "jyear",
                groupNumber: 2,
                plusParam: { jyears: offset },
            };
        })
        .reverse();
}

function getCustomPeriodOptions(optionsParams) {
    const { customOptions } = optionsParams;
    return customOptions.map((option) => ({
        id: option.id,
        description: option.description,
        granularity: "withDomain",
        groupNumber: 3,
        domain: option.domain,
    }));
}

if (odoo.user_calendar_type === "jalaali") {
    search_dates.QUARTER_OPTIONS = jQUARTER_OPTIONS;
    search_dates.getPeriodOptions = function (referenceMoment, optionsParams) {
        return [
            ...jgetMonthPeriodOptions(referenceMoment, optionsParams),
            ...jgetQuarterPeriodOptions(optionsParams),
            ...jgetYearPeriodOptions(referenceMoment, optionsParams),
            ...getCustomPeriodOptions(optionsParams),
        ];
    }
}

search_dates.getSetParam = function (periodOption, referenceMoment) {
    ////////// overrided //////////
    // if (periodOption.granularity === "quarter") {
    if (periodOption.granularity.replace("j", "") === "quarter") {
    ////////// ///////// //////////
        return periodOption.setParam;
    }
    const date = referenceMoment.plus(periodOption.plusParam);
    const granularity = periodOption.granularity;
    const setParam = { [granularity]: date[granularity] };
    return setParam;
}

search_dates.getSelectedOptions = function (referenceMoment, searchItem, selectedOptionIds) {
    ////////// Overrided //////////
    // const selectedOptions = { year: [] };
    const selectedOptions = odoo.user_calendar_type === "jalaali" ? { jyear: [] } : { year: [] };
    ////////// ///////// //////////
    const periodOptions = search_dates.getPeriodOptions(referenceMoment, searchItem.optionsParams);
    for (const optionId of selectedOptionIds) {
        const option = periodOptions.find((option) => option.id === optionId);
        const granularity = option.granularity;
        if (!selectedOptions[granularity]) {
            selectedOptions[granularity] = [];
        }
        if (option.domain) {
            selectedOptions[granularity].push(pick(option, "domain", "description"));
        } else {
            const setParam = search_dates.getSetParam(option, referenceMoment);
            selectedOptions[granularity].push({ granularity, setParam });
        }
    }
    return selectedOptions;
}

search_dates.getComparisonParams = function(referenceMoment, searchItem, selectedOptionIds, comparisonOptionId) {
    const comparisonOption = search_dates.COMPARISON_OPTIONS[comparisonOptionId];
    const selectedOptions = search_dates.getSelectedOptions(referenceMoment, searchItem, selectedOptionIds);
    if (comparisonOption.plusParam) {
        return [comparisonOption.plusParam, selectedOptions];
    }
    const plusParam = {};
    let globalGranularity = "year";
    if (selectedOptions.month) {
        globalGranularity = "month";
    } else if (selectedOptions.quarter) {
        globalGranularity = "quarter";
    }
    ////////// Overrided //////////
    if (odoo.user_calendar_type === "jalaali") {
        globalGranularity = 'jyear';
        if (selectedOptions.jmonth) {
            globalGranularity = 'jmonth';
        } else if (selectedOptions.jquarter) {
            globalGranularity = 'jquarter';
        }
    }
    ////////// ///////// //////////
    const granularityFactor = PER_YEAR[globalGranularity];
    ////////// Overrided //////////
    // const years = selectedOptions.year.map(o => o.setParam.year);
    const years = odoo.user_calendar_type === "jalaali" ? selectedOptions.jyear.map(o => o.setParam.jyear) : selectedOptions.year.map(o => o.setParam.year);
    ////////// ///////// //////////
    const yearMin = Math.min(...years);
    const yearMax = Math.max(...years);
    let optionMin = 0;
    let optionMax = 0;
    if (selectedOptions.quarter) {
        const quarters = selectedOptions.quarter.map((o) => o.setParam.quarter);
        if (globalGranularity === "month") {
            delete selectedOptions.quarter;
            for (const quarter of quarters) {
                for (const month of QUARTERS[quarter].coveredMonths) {
                    const monthOption = selectedOptions.month.find(
                        (o) => o.setParam.month === month
                    );
                    if (!monthOption) {
                        selectedOptions.month.push({
                            setParam: { month },
                            granularity: "month",
                        });
                    }
                }
            }
        } else {
            optionMin = Math.min(...quarters);
            optionMax = Math.max(...quarters);
        }
    }
    ////////// Overrided //////////
    if (selectedOptions.jquarter) {
        const quarters = selectedOptions.jquarter.map(o => o.setParam.jquarter);
        if (globalGranularity === 'jmonth') {
            delete selectedOptions.jquarter;
            for (const quarter of quarters) {
                for (const month of QUARTERS[quarter].coveredMonths) {
                    const monthOption = selectedOptions.jmonth.find(
                        o => o.setParam.jmonth === month
                    );
                    if (!monthOption) {
                        selectedOptions.jmonth.push({
                            setParam: { jmonth:month, }, granularity: 'jmonth',
                        });
                    }
                }
            }
        } else {
            optionMin = Math.min(...quarters);
            optionMax = Math.max(...quarters);
        }
    }
    ////////// ///////// //////////
    if (selectedOptions.month) {
        const months = selectedOptions.month.map((o) => o.setParam.month);
        optionMin = Math.min(...months);
        optionMax = Math.max(...months);
    }
    ////////// Overrided //////////
    if (selectedOptions.jmonth) {
        const months = selectedOptions.jmonth.map(o => o.setParam.jmonth);
        optionMin = Math.min(...months);
        optionMax = Math.max(...months);
    }
    ////////// ///////// //////////
    const num = -1 + granularityFactor * (yearMin - yearMax) + optionMin - optionMax;
    const key =
        globalGranularity === "year"
            ? "years"
            : globalGranularity === "month"
            ? "months"
            : "quarters";
    ////////// Overrided //////////
    if (odoo.user_calendar_type === "jalaali") {
        const key =
        globalGranularity === "year"
            ? "jyears"
            : globalGranularity === "month"
            ? "jmonths"
            : "jquarters";
    }
    ////////// ///////// //////////
    plusParam[key] = num;
    return [plusParam, selectedOptions];
}

search_dates.constructDateRange = function(params) {
    const { referenceMoment, fieldName, fieldType, granularity, setParam, plusParam } = params;
    if ("quarter" in setParam) {
        // Luxon does not consider quarter key in setParam (like moment did)
        setParam.month = QUARTERS[setParam.quarter].coveredMonths[0];
        delete setParam.quarter;
    }
    ////////// Overrided //////////
    if ("jquarter" in setParam) {
        // Luxon does not consider quarter key in setParam (like moment did)
        setParam.jmonth = QUARTERS[setParam.jquarter].coveredMonths[0];
        delete setParam.jquarter;
    }
    ////////// ///////// //////////
    const date = referenceMoment.set(setParam).plus(plusParam || {});
    // compute domain
    const leftDate = date.startOf(granularity);
    const rightDate = date.endOf(granularity);
    let leftBound;
    let rightBound;
    if (fieldType === "date") {
        leftBound = serializeDate(leftDate);
        rightBound = serializeDate(rightDate);
    } else {
        leftBound = serializeDateTime(leftDate);
        rightBound = serializeDateTime(rightDate);
    }
    const domain = new Domain(["&", [fieldName, ">=", leftBound], [fieldName, "<=", rightBound]]);
    // compute description
    ////////// Overrided //////////
    // const descriptions = [date.toFormat("yyyy")];
    const descriptions = [date.toFormat(odoo.user_calendar_type === "jalaali" ? "jyyyy" : "yyyy")];
    ////////// ///////// //////////
    const method = localization.direction === "rtl" ? "push" : "unshift";
    ////////// Overrided //////////
    // if (granularity === "month") {
    //     descriptions[method](date.toFormat("MMMM"));
    // } else if (granularity === "quarter") {
    //     const quarter = date.quarter;
    //     descriptions[method](QUARTERS[quarter].description.toString());
    // }
    switch (granularity) {
        case "month":
            descriptions[method](date.toFormat("MMMM"));
            break;
        case "quarter":
            descriptions[method](QUARTERS[date.quarter].description.toString());
            break;
        case "jmonth":
            descriptions[method](date.toFormat("jMMMM"));
            break;
        case "jquarter":
            descriptions[method](QUARTERS[date.jquarter].description.toString());
            break;
    }
    ////////// ///////// //////////
    const description = descriptions.join(" ");
    return { domain, description };
}


search_dates.constructDateDomain = function(
    referenceMoment,
    searchItem,
    selectedOptionIds,
    comparisonOptionId
) {
    let plusParam;
    let selectedOptions;
    if (comparisonOptionId) {
        [plusParam, selectedOptions] = getComparisonParams(
            referenceMoment,
            searchItem,
            selectedOptionIds,
            comparisonOptionId
        );
    } else {
        selectedOptions = search_dates.getSelectedOptions(referenceMoment, searchItem, selectedOptionIds);
    }
    if ("withDomain" in selectedOptions) {
        return {
            description: selectedOptions.withDomain[0].description,
            domain: Domain.and([selectedOptions.withDomain[0].domain, searchItem.domain]),
        };
    }
    ////////// Overrided //////////
    // const yearOptions = selectedOptions.year;
    // const otherOptions = [...(selectedOptions.quarter || []), ...(selectedOptions.month || [])];
    var yearOptions = selectedOptions.year;
    var otherOptions = [...(selectedOptions.quarter || []), ...(selectedOptions.month || [])];
    if (odoo.user_calendar_type === "jalaali") {
        var yearOptions = selectedOptions.jyear;
        var otherOptions = [...(selectedOptions.jquarter || []), ...(selectedOptions.jmonth || [])];          
    }
    ////////// ///////// //////////
    search_dates.sortPeriodOptions(yearOptions);
    search_dates.sortPeriodOptions(otherOptions);
    const ranges = [];
    const { fieldName, fieldType } = searchItem;
    for (const yearOption of yearOptions) {
        const constructRangeParams = {
            referenceMoment,
            fieldName,
            fieldType,
            plusParam,
        };
        if (otherOptions.length) {
            for (const option of otherOptions) {
                const setParam = Object.assign(
                    {},
                    yearOption.setParam,
                    option ? option.setParam : {}
                );
                const { granularity } = option;
                const range = search_dates.constructDateRange(
                    Object.assign({ granularity, setParam }, constructRangeParams)
                );
                ranges.push(range);
            }
        } else {
            const { granularity, setParam } = yearOption;
            const range = search_dates.constructDateRange(
                Object.assign({ granularity, setParam }, constructRangeParams)
            );
            ranges.push(range);
        }
    }
    let domain = Domain.combine(
        ranges.map((range) => range.domain),
        "OR"
    );
    domain = Domain.and([domain, searchItem.domain]);
    const description = ranges.map((range) => range.description).join("/");
    return { domain, description };
}