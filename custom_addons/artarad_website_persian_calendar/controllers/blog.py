# -*- coding: utf-8 -*-
from odoo import http, fields, api, tools, models
from odoo.http import request
from odoo.addons.website_blog.controllers.main import WebsiteBlog
from odoo.tools.misc import get_lang

import jdatetime
import pytz
import babel.dates
from collections import defaultdict

def get_month(date):
    date_from = jdatetime.datetime(date.year, date.month, 1, 0, 0, 0)

    if date.month <= 6:
        date_to = jdatetime.datetime(date.year, date.month, 31, 23, 59, 59)
    elif date.month <= 11:
        date_to = jdatetime.datetime(date.year, date.month, 30, 23, 59, 59)
    else:
        if date.isleap():
            date_to = jdatetime.datetime(date.year, date.month, 30, 23, 59, 59)
        else:
            date_to = jdatetime.datetime(date.year, date.month, 29, 23, 59, 59)
    return date_from, date_to


class artaradWebsiteBlog(WebsiteBlog):
    def nav_list(self, blog=None):
        dom = blog and [('blog_id', '=', blog.id)] or []
        if not request.env.user.has_group('website.group_website_designer'):
            dom += [('post_date', '<=', fields.Datetime.now())]

        ########## overrided #########
        # groups = request.env['blog.post']._read_group(
        # dom, groupby=['post_date:month'])
        if get_lang(request.env).code == "fa_IR":
            group_dates = set()
            for post in request.env['blog.post'].sudo().search(dom):
                j_post_date = get_month(jdatetime.datetime.fromgregorian(datetime=post.post_date).replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Tehran')))
                group_dates.add(j_post_date)
            
            res = defaultdict(list)
            for group_date in group_dates:
                year = str(group_date[0].year)
                res[year].append({
                    'date_begin': group_date[0].togregorian().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
                    'date_end': group_date[1].togregorian().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
                    'month': group_date[0].strftime("%B"),
                    'year': year,
                })
        else:
            group_dates = set()
            for post in request.env['blog.post'].sudo().search(dom):
                group_dates.add(post.post_date.replace(day=1, hour=0, minute=0, second=0))
            groups = [(item,) for item in group_dates]
            
            locale = get_lang(request.env).code
            tzinfo = pytz.timezone(request.context.get('tz', 'utc') or 'utc')
            fmt = tools.DEFAULT_SERVER_DATETIME_FORMAT

            res = defaultdict(list)
            for [start] in groups:
                year = babel.dates.format_datetime(start, format='yyyy', tzinfo=tzinfo, locale=locale)
                res[year].append({
                    'date_begin': start.strftime(fmt),
                    'date_end': (start + models.READ_GROUP_TIME_GRANULARITY['month']).strftime(fmt),
                    'month': babel.dates.format_datetime(start, format='MMMM', tzinfo=tzinfo, locale=locale),
                    'year': year,
                })
        ########## ######### #########
        return res