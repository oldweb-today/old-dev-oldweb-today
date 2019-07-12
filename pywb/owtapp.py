from gevent.monkey import patch_all; patch_all()

from pywb.apps.frontendapp import FrontEndApp
from warcio.timeutils import http_date_to_datetime, timestamp_now

from tempfile import SpooledTemporaryFile

import os
import redis
import logging
import traceback
import re

from pywb.warcserver.warcserver import register_source
from pywb.warcserver.index.indexsource import LiveIndexSource, FileIndexSource, NotFoundException


# ============================================================================
class OWTProxyApp(FrontEndApp):
    FIND_COLL_RX = re.compile(r'collection="([^"]+)"')

    def __init__(self, config_file=None, custom_config=None):
        super(OWTProxyApp, self).__init__(config_file='./config.yaml',
                                           custom_config=custom_config)

        self.redis = redis.StrictRedis.from_url(os.environ['REDIS_URL'], decode_responses=True)

    def proxy_route_request(self, url, environ):
        try:
            key = 'up:' + environ['REMOTE_ADDR']
            timestamp = self.redis.hget(key, 'timestamp') or timestamp_now()
            environ['pywb_redis_key'] = key
            environ['pywb_proxy_default_timestamp'] = timestamp
        except Exception as e:
            traceback.print_exc()

        return self.proxy_prefix + url

    def serve_content(self, environ, *args, **kwargs):
        response = super(OWTProxyApp, self).serve_content(environ, *args, **kwargs)

        memento_dt = response.status_headers.get('Memento-Datetime', '')
        link = response.status_headers.get('Link', '')

        if link:
            try:
                m = self.FIND_COLL_RX.search(link)
                if m:
                    self.redis.hincrby(environ['pywb_redis_key'], 'stats:src:' + m.group(1), 1)
            except Exception:
                traceback.print_exc()

        if memento_dt:
            try:
                timestamp = http_date_to_datetime(memento_dt).timestamp()

                url = kwargs.get('url')
                # should start with id_/
                if url:
                    url = url[4:]

                self.redis.zadd(environ['pywb_redis_key'] + ':z', timestamp, url)
            except Exception:
                traceback.print_exc()

        return response


#=============================================================================
application = OWTProxyApp()

