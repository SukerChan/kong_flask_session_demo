import logging
import os
import sys
from pprint import pprint

from dotenv import load_dotenv
from flask import Flask, jsonify, request, make_response, redirect, url_for

load_dotenv()


def get_config(key, default=None):
    return os.environ.get(key, default)


APP_NAME = get_config('APP_NAME', 'kong_flask_demo')
USER_ID_PREFIX = APP_NAME + '_'

app = Flask(__name__)
app.secret_key = APP_NAME
app.session_cookie_name = 'fsession'


# REDIS_KEY_PREFIX = APP_NAME + '_'
# USER_ID_KEY = REDIS_KEY_PREFIX + 'user_id'
# USERNAME_KEY = REDIS_KEY_PREFIX + 'user_name'
# MAX_USER_ID_KEY = REDIS_KEY_PREFIX + 'max_user_id'

def get_kong_api():
    from kong_api import KongAPI

    host = get_config('KONG_HOST')
    port = int(get_config('KONG_ADMIN_PORT', 8001))
    protocol = get_config('KONG_PROTOCOL', 'http')
    api = KongAPI(host, port, protocol)
    return api


def generate_user_id():
    max_user_id = 0

    api = get_kong_api()
    for custom in api.get_consumers():
        if not custom.contain_tag(APP_NAME) or not custom.custom_id:
            continue

        user_id = User.trans_custom_id_to_user_id(custom.custom_id)
        if user_id:
            max_user_id = max(user_id, max_user_id)

    return max_user_id + 1


class User:
    def __init__(self, user_id=None, username=None, is_anonymous=False):
        self.__username = username
        self.__id = user_id
        self.__is_anonymous = is_anonymous

        self.__json = {'is_anonymous': self.__is_anonymous}
        if not self.__is_anonymous:
            self.__json['id'] = self.__id
            self.__json['username'] = self.__username

    @property
    def id_(self):
        return self.__id

    @property
    def username(self):
        return self.__username

    @property
    def is_anonymous(self):
        return self.__is_anonymous

    @classmethod
    def get_by_id(cls, user_id):
        custom_id = USER_ID_PREFIX + user_id

        api = get_kong_api()
        for consumer in api.get_consumers():
            if consumer.custom_id == custom_id and consumer.contain_tag(APP_NAME):
                return User(user_id, consumer.username)

    @classmethod
    def get_by_name(cls, username):
        api = get_kong_api()
        consumer = api.get_consumer(username)
        if consumer and consumer.contain_tag(APP_NAME) and consumer.custom_id:
            user_id = cls.trans_custom_id_to_user_id(consumer.custom_id)
            user = User(user_id, username)
            return user

        # with get_redis() as r:
        #     if not r.hexists(USERNAME_KEY, username):
        #         return None
        #     return cls(int(r.hget(USERNAME_KEY, username)), username)

    @classmethod
    def new_user(cls, username):
        try:
            api = get_kong_api()
            user_id = generate_user_id()
            api.add_consumer(username, cls.trans_user_id_to_custom_id(user_id), tags=[APP_NAME])
            user = User(user_id, username)
            return user
        except:
            logging.exception('Create user fail')
            raise

            # with get_redis() as r:
        #     if r.hexists(USERNAME_KEY, username):
        #         raise ValueError('User of name {} already exists')
        #     max_id = r.get(MAX_USER_ID_KEY)
        #     if max_id:
        #         max_id = int(max_id)
        #     else:
        #         max_id = 0
        #
        #     user_id = max_id + 1
        #     r.hset(USER_ID_KEY, user_id, username)
        #     r.hset(USERNAME_KEY, username, user_id)
        #     r.set(MAX_USER_ID_KEY, user_id)
        #     return cls(user_id, username)

    @classmethod
    def trans_custom_id_to_user_id(cls, custom_id):
        if custom_id:
            user_id = custom_id.replace(USER_ID_PREFIX, '')
            return int(user_id)

    @classmethod
    def trans_user_id_to_custom_id(cls, user_id):
        return '{}{}'.format(USER_ID_PREFIX, user_id)

    def to_json(self):
        return self.__json


def is_anonymous():
    anonymous = request.headers.get('X-Anonymous-Consumer', type=bool)
    # logging.debug(type(anonymous))
    # logging.debug(anonymous)
    return anonymous is True


def get_current_user():
    if is_anonymous():
        return User(is_anonymous=True)

    username = request.headers.get('X-Consumer-Username', type=str)
    custom_id = request.headers.get('X-Consumer-Custom-Id', type=str)
    user_id = User.trans_custom_id_to_user_id(custom_id)
    return User(user_id, username)


def login_user(user):
    api = get_kong_api()

    key = api.get_consumer_key(user.username)
    response = api.login_consumer_key(get_config('KONG_FLASK_LOGIN_URL'), key, request.headers)

    cookie = response.cookies.get(get_config('KONG_COOKIE_NAME'))
    # logging.debug(response.headers)
    # logging.debug(response.cookies)
    # logging.debug(cookie)

    return cookie


def logout_user():
    response = make_response(jsonify({
        'msg': 'success',
        'request_headers': request.headers.to_wsgi_list()
    }))

    response.delete_cookie(get_config('KONG_COOKIE_NAME'))
    return response


@app.route('/')
def hello():
    print(request.headers)

    ret = {
        'msg': 'hello',
        'request_headers': request.headers.to_wsgi_list()
    }

    user = get_current_user()
    ret.update(user.to_json())
    return jsonify(ret)


@app.route('/login/<username>')
def login(username):
    current_user = get_current_user()
    if not current_user.is_anonymous:
        if current_user.username == username:
            ret = {
                'msg': 'already login',
                'username': username,
                'user_id': current_user.id_
            }
        else:
            ret = {
                'msg': 'login fail, already login status',
                'username': current_user.username
            }
    else:
        user = User.get_by_name(username)
        if not user:
            ret = {
                'msg': 'user {} not exists',
                'username': username
            }
        else:
            cookie = login_user(user)
            if not cookie:
                ret = {
                    'msg': "Can't get cookie for kong session auth"
                }
            else:
                ret = {'msg': 'success', 'username': username, 'user_id': user.id_,
                       'request_headers': request.headers.to_wsgi_list()}
                response = make_response(jsonify(ret))
                response.set_cookie(get_config('KONG_COOKIE_NAME'), cookie)
                return response

    ret['request_headers'] = request.headers.to_wsgi_list()

    return jsonify(ret)


@app.route('/logout')
def logout():
    current_user = get_current_user()
    if current_user.is_anonymous:
        ret = {
            'msg': 'already logout'
        }
    else:
        response = logout_user()
        return response

    ret['request_headers'] = request.headers.to_wsgi_list()

    return jsonify(ret)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    # pprint(app.config)

    app.run(host='0.0.0.0', port=get_config('FLASK_PORT', 6321), debug=True)
