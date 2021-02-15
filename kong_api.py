import logging
import sys
from collections import namedtuple
from urllib.parse import urljoin

import requests


class KongCustomer:
    __KONG_CUSTOMER = namedtuple('KONG_CUSTOMER', ('id', 'created_at', 'username', 'custom_id', 'tags'))

    def __init__(self, id_, created_at, username, custom_id, tags):
        self.__customer = self.__KONG_CUSTOMER(id_, created_at, username, custom_id, tags)

    def to_json(self):
        return dict(self.__customer._asdict())

    @property
    def id_(self):
        return self.__customer.id

    @property
    def username(self):
        return self.__customer.username

    @property
    def custom_id(self):
        return self.__customer.custom_id

    @property
    def tags(self):
        return self.__customer.tags

    def contain_tag(self, tag):
        return tag in self.__customer.tags

    @classmethod
    def from_json(cls, json_dict: dict):
        id_ = json_dict.get('id')
        created_at = json_dict.get('created_at')
        username = json_dict.get('username')
        custom_id = json_dict.get('custom_id')
        tags = json_dict.get('tags')
        if isinstance(tags, list):
            tags = set(tags)

        return cls(id_, created_at, username, custom_id, tags)

    def __repr__(self):
        return str(self.to_json())


class KongAPI:
    def __init__(self, host, port, protocol='http'):
        self.host = host
        self.port = port

        self.base_url = '{}://{}:{}'.format(protocol, host, port)

    def add_consumer(self, username=None, custom_id=None, tags=None):
        if not username and not custom_id:
            raise ValueError('Either username or custom_id should be set')
        url = urljoin(self.base_url, 'consumers')
        json_data = dict()
        if username:
            json_data['username'] = username
        if custom_id:
            json_data['custom_id'] = custom_id
        if tags:
            json_data['tags'] = tags
        response = requests.post(url, json=json_data)
        logging.debug(response.content)
        response.raise_for_status()
        ret = response.json()
        return KongCustomer.from_json(ret)

    def get_consumers(self):
        consumers = list()
        url = urljoin(self.base_url, 'consumers')
        # logging.debug(url)
        while True:
            response = requests.get(url)
            response.raise_for_status()
            ret = response.json()
            for consumer_json in ret['data']:
                consumers.append(KongCustomer.from_json(consumer_json))
            if ret['next']:
                url = ret['next']
            else:
                break
        return consumers

    def get_consumer(self, username_or_id):
        if not username_or_id:
            raise ValueError('Please input username or consumer id')
        url = urljoin(self.base_url, 'consumers/{}'.format(username_or_id))
        response = requests.get(url)
        response.raise_for_status()
        ret = response.json()
        return KongCustomer.from_json(ret)

    def update_consumer(self, username_or_id, new_username=None, custom_id=None, tags=None):
        if not username_or_id:
            raise ValueError('Please input username or consumer id')
        if not new_username and not custom_id:
            raise ValueError('Either new_username or custom_id should be set')
        url = urljoin(self.base_url, 'consumers/{}'.format(username_or_id))
        data = dict()
        if new_username:
            data['username'] = new_username
        if custom_id:
            data['custom_id'] = custom_id
        if tags:
            data['tags'] = tags
        response = requests.patch(url, data=data)
        response.raise_for_status()
        ret = response.json()
        return KongCustomer.from_json(ret)

    def delete_consumer(self, username_or_id):
        if not username_or_id:
            raise ValueError('Please input username or consumer id')
        url = urljoin(self.base_url, 'consumers/{}'.format(username_or_id))
        response = requests.delete(url)
        response.raise_for_status()

    def login_consumer_basic(self, login_url, username, password):
        # todo
        pass

    def login_consumer_key(self, login_url, key):
        from utils import add_url_params

        url = add_url_params(login_url, {'apikey': key})
        response = requests.get(url)
        response.raise_for_status()
        return response

    def get_consumer_password(self, username_or_id):
        # todo
        pass

    def get_consumer_key(self, username_or_id):
        if not username_or_id:
            raise ValueError('Please input username or consumer id')

        url = urljoin(self.base_url, 'consumers/{}/key-auth'.format(username_or_id))
        response = requests.get(url)
        response.raise_for_status()

        # logging.debug(response.json())
        ret = response.json()
        if ret['data']:
            return ret['data'][0].get('key')


def test():
    from app import get_config

    host = get_config('KONG_HOST')
    port = int(get_config('KONG_ADMIN_PORT', 8001))
    protocol = get_config('KONG_PROTOCOL', 'http')
    api = KongAPI(host, port, protocol)
    # ret = api.get_consumers()
    # ret = api.get_consumer('suker')
    # ret = api.add_consumer('chenyulong')
    # ret = api.update_consumer('chenyulong', custom_id='234')
    ret = api.get_consumer_key('suker')
    response = api.login_consumer_key('{}://{}:{}/{}'.format(protocol, host, 8000, get_config('APP_NAME')), ret)
    logging.debug(response.cookies)
    logging.debug(response.cookies.get(get_config('KONG_COOKIE_NAME')))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    test()
