from app import application
from flask import Flask, request, Response, render_template
import json


def to_json(data):
    return Response(json.dumps(data), mimetype='application/json')


def init_owt_routes(app):
    @app.route('/browse/<image_name>/<path:url>')
    def owt_replay(image_name, url):
        if request.query_string:
            url += '?' + request.query_string.decode('utf-8')

        view_url = '/view/' + image_name + '/' + url

        timestamp, url = app.parse_url_ts(url)
        return render_template('replay.html',
                               url=url,
                               timestamp=timestamp,
                               image_name=image_name,
                               view_url=view_url,
                               include_datetime=True)


    @app.route('/api/stats/<reqid>')
    def owt_stats(reqid):
        res = app.shepherd.redis.get('req:' + reqid)
        if not res:
            return to_json({'error': 'not_found'})

        try:
            data = json.loads(res)
            ip = data['resp']['containers']['browser']['ip']
            key = 'up:' + ip

            # get stats
            stats = {}

            up_data = app.shepherd.redis.hgetall(key)

            # host stats
            hosts = []

            for name, value in up_data.items():
                if name.startswith('stats:src:'):
                    hosts.append(name.rsplit(':', 1)[-1])

            stats['hosts'] = hosts

            # url stats
            zset = key + ':z'

            stats['urls'] = app.shepherd.redis.zcard(zset)

            stats['min_sec'] = app.shepherd.redis.zrange(zset, 0, 0, withscores=True)[-1][1]
            stats['max_sec'] = app.shepherd.redis.zrange(zset, -1, -1, withscores=True)[-1][1]

            stats['ttl'] = app.shepherd.redis.ttl('p:fixed-pool:rq:' + reqid)

            # page url + timestamp (secs)
            url = up_data.get('URL')
            score = None
            if url and not url.startswith(('http:', 'https:')):
                url = 'http://' + url

            if url:
                score = app.shepherd.redis.zscore(zset, url)

            print(url)
            print(score)
            if score:
                stats['page_url'] = url
                stats['page_url_secs'] = score

            return to_json(stats)

        except Exception as e:
            print(e)
            return to_json({'error': 'not_found'})


init_owt_routes(application)


# ============================================================================
if __name__ == '__main__':
    from gevent.pywsgi import WSGIServer
    WSGIServer(('0.0.0.0', 9020), application).serve_forever()



