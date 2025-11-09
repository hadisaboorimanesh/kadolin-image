# -*- coding: utf-8 -*-
import logging

from odoo import http, tools
from odoo.tools.func import lazy_property

from .odoo.redis_session import RedisSessionStore


_logger = logging.getLogger(__name__)

if tools.config.get('redis_enable', False):
    @lazy_property
    def session_store(self):
        _logger.info('HTTP sessions stored in the Redis server')
        return RedisSessionStore(session_class=http.Session)
    http.root.session_store = RedisSessionStore(session_class=http.Session)
