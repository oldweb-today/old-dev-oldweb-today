from app import application
from flask import Blueprint, jsonify
import json


def init_owt_routes(app, shepherd):
    @app.route('/api/stats/<reqid>')
    def owt_stats(reqid):
        res = shepherd.redis.get('req:' + reqid)
        if not res:
            return jsonify(error='not_found')

        try:
            data = json.loads(res)
            ip = data['resp']['containers']['browser']['ip']
            key = 'up:' + ip

            # get stats
            stats = {}

            up_data = shepherd.redis.hgetall(key)

            # host stats
            hosts = []

            for name, value in up_data.items():
                if name.startswith('stats:src:'):
                    hosts.append(name.rsplit(':', 1)[-1])

            stats['hosts'] = hosts

            # url stats
            zset = key + ':z'

            stats['urls'] = shepherd.redis.zcard(zset)

            stats['min_sec'] = shepherd.redis.zrange(zset, 0, 0, withscores=True)[-1][1]
            stats['max_sec'] = shepherd.redis.zrange(zset, -1, -1, withscores=True)[-1][1]

            stats['ttl'] = shepherd.redis.ttl('p:fixed-pool:rq:' + reqid)

            # page url + timestamp (secs)
            url = up_data.get('url')
            score = None
            if url and not url.startswith(('http:', 'https:')):
                url = 'http://' + url

            if url:
                score = shepherd.redis.zscore(zset, url)

            if score:
                stats['page_url'] = url
                stats['page_url_secs'] = score

            return jsonify(stats)

        except Exception as e:
            print(e)
            return jsonify(error='not_found')


def main():
    owt = Blueprint('owt', 'owt', template_folder='owt_templates', static_folder='static')
    init_owt_routes(owt, application.shepherd)
    application.register_blueprint(owt)


main()


# ============================================================================
if __name__ == '__main__':
    from gevent.pywsgi import WSGIServer
    WSGIServer(('0.0.0.0', 9020), application).serve_forever()



