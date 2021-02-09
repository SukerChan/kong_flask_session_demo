import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_login import LoginManager, current_user, UserMixin, login_user, logout_user

from redis_utils import get_redis

load_dotenv()

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

app.secret_key = os.environ.get('APP_SECRET_KEY', 'kong_flask_demo')

REDIS_KEY_PREFIX = 'kong_flask_demo_'
USER_ID_KEY = REDIS_KEY_PREFIX + 'user_id'
USERNAME_KEY = REDIS_KEY_PREFIX + 'user_name'
MAX_USER_ID_KEY = REDIS_KEY_PREFIX + 'max_user_id'


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


class User(UserMixin):
    def __init__(self, user_id, username):
        self.username = username
        self.id = user_id

    @classmethod
    def get_by_id(cls, user_id):
        with get_redis() as r:
            if not r.hexists(USER_ID_KEY, user_id):
                return None
            return cls(user_id, r.hget(USER_ID_KEY, user_id).decode())

    @classmethod
    def get_by_name(cls, username):
        with get_redis() as r:
            if not r.hexists(USERNAME_KEY, username):
                return None
            return cls(int(r.hget(USERNAME_KEY, username)), username)

    @classmethod
    def new_user(cls, username):
        with get_redis() as r:
            if r.hexists(USERNAME_KEY, username):
                raise ValueError('User of name {} already exists')
            max_id = r.get(MAX_USER_ID_KEY)
            if max_id:
                max_id = int(max_id)
            else:
                max_id = 0

            user_id = max_id + 1
            r.hset(USER_ID_KEY, user_id, username)
            r.hset(USERNAME_KEY, username, user_id)
            r.set(MAX_USER_ID_KEY, user_id)
            return cls(user_id, username)


@app.route('/')
def hello():
    ret = {
        'msg': 'hello',
    }
    if current_user.is_anonymous:
        ret['anonymous'] = True
    else:
        ret['anonymous'] = False
        ret['username'] = current_user.username
    return jsonify(ret)


@app.route('/login/<username>')
def login(username):
    if current_user.is_anonymous:
        user = User.get_by_name(username)
        if not user:
            user = User.new_user(username)

        login_user(user)
        return jsonify({
            'msg': 'success',
            'username': username
        })

    if current_user.username == username:
        return jsonify({
            'msg': 'already login',
            'username': username
        })

    return jsonify({
        'msg': 'login fail, already login status',
        'username': current_user.username
    })


@app.route('/logout')
def logout():
    if current_user.is_anonymous:
        return jsonify({
            'msg': 'already logout'
        })

    logout_user()
    return jsonify({
        'msg': 'success'
    })


if __name__ == '__main__':
    app.run(port=6321)
