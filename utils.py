import logging
import sys


def add_url_params(url, params):
    import urllib.parse as urlparse
    from urllib.parse import urlencode

    pr = urlparse.urlparse(url)
    qs = dict(urlparse.parse_qsl(pr.query))
    qs.update(params)

    pr = pr._replace(query=urlencode(qs))
    new_url = pr.geturl()

    return new_url


def demo():
    url = 'http://abc.efg'
    params = {'b': 4}

    logging.debug(add_url_params(url, params))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    demo()
