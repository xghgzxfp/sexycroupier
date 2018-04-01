# coding: utf-8

import functools
import requests

from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import Flask, session, render_template, request, redirect, url_for, g, abort
from pymongo import MongoClient

from . import config

app = Flask(__name__)
app.config.from_object(config)
db = app.db = MongoClient(app.config['MONGO_URI'])[app.config['MONGO_DBNAME']]

from . import model

title = "2018 World Cup"


def next_url():
    return request.args.get('next') or request.referrer or url_for('index')


def authenticated(f):
    @functools.wraps(f)
    def _(*args, **kwargs):
        if not g.me:
            # 非微信或未设置微信 credentials 则以“迷你钻”身份登录 仅供 DEBUG
            if ('MicroMessenger' not in request.user_agent.string
                    or not (app.config['WECHAT_APPID'] and app.config['WECHAT_APPSECRET'])):
                session['openid'] = 'wechat-openid-minizuan'
                return render_template('signup.html', gambler='迷你钻')
            # 重定向至微信获取授权
            wx_auth_base = 'https://open.weixin.qq.com/connect/oauth2/authorize?'
            wx_auth_params = dict(                          # 参数需按字典序 Python 3.6+ dict 确保有序
                appid=app.config['WECHAT_APPID'],
                redirect_uri=url_for('auth_complete', next=request.full_path, _external=True,),
                response_type='code',
                scope='snsapi_base',
                state=request.endpoint,
            )
            return redirect(wx_auth_base + urlencode(wx_auth_params) + '#wechat_redirect')
        return f(*args, **kwargs)
    return _


@app.before_request
def before_request():
    openid = session.get('openid')
    g.me = model.find_gambler_by_openid(openid)


@app.route('/auth/complete', methods=['GET'])
def auth_complete():
    if g.me:
        return redirect(next_url())

    code = request.args.get('code')

    wx_token_base = 'https://api.weixin.qq.com/sns/oauth2/access_token?'
    wx_token_params = dict(
        appid=app.config['WECHAT_APPID'],
        secret=app.config['WECHAT_APPSECRET'],
        code=code,
        grant_type='authorization_code',
    )

    retry = 5
    while retry:
        try:
            openid = requests.get(wx_token_base + urlencode(wx_token_params), timeout=3).json()['openid']
        except (IOError, ValueError, KeyError) as e:
            retry -= 1
            if not retry:
                # 获取 openid 失败
                return abort(401)
        else:
            break

    session['openid'] = openid

    me = model.find_gambler_by_openid(openid)
    if not me:
        return render_template('signup.html')

    return redirect(next_url())


@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    if g.me:
        return redirect(next_url())

    name = request.form.get('gambler')
    openid = session.get('openid')

    # 正常流程下 name 和 openid 均不可能为空
    if not name or not openid:
        return abort(401)

    model.insert_gambler(name, openid)

    return redirect(url_for('index'))


@app.route('/')
@authenticated
def index():
    userteams = []
    today = datetime.now()
    dayaftertomorrow = today + timedelta(days=2)

    #games = db.match.find({"$and": [{"match_time": {"$gte": today}},
    #                         {"match_time": {"$lt": dayaftertomorrow}}]}).sort({"match_time": -1})
    games = db.match.find().sort([("match_time", -1)])
    return render_template('index.html', username=g.me.name, userteams=userteams, games=list(games))


@app.route('/bet', methods=['POST'])
@authenticated
def bet():
    match_id = request.values.get("match_id")
    new_choice = request.values.get("betchoice")
    ## function place holder:
    ## check if current time is an effective time point to modify the bet choice

    model.update_match_gamblers(match_id, new_choice, g.me.name)
    return redirect(next_url())


if __name__ == "__main__":
    app.run(port=8010)
