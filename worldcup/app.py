# coding: utf-8

import datetime
import functools
import requests

from urllib.parse import urlencode
from flask import Flask, session, render_template, request, redirect, url_for, g, abort
from pymongo import MongoClient
from . import config
from werkzeug.local import LocalProxy


app = Flask(__name__)
app.config.from_object(config)

dbclient = app.dbclient = MongoClient(app.config['MONGO_URI'])
logindb = app.logindb = dbclient[app.config['MONGO_LOGINDB']]

def get_tournamentdb(tournament=None):
    g.tournament = tournament or (g.tournament if 'tournament' in g else app.config['DEFAULT_TOURNAMENT'])
    g.tournamentdb = dbclient[g.tournament.dbname]
    return g.tournamentdb

with app.app_context():
    tournamentdb = app.tournamentdb = LocalProxy(get_tournamentdb)

from . import model

title = '2018 World Cup'

@app.template_filter('_ts')
def _ts(time: datetime.datetime) -> int:
    """把以 naive datetime 表示的北京时间正确转换为 unix timestamp"""
    return time.replace(tzinfo=datetime.timezone.utc).timestamp() - 8 * 3600


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
    g.me = model.find_user_by_openid(openid)
    # will support dbname switch in future
    g.tournament = session.get('tourna,ent', app.config['DEFAULT_TOURNAMENT'])


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

    me = model.find_user_by_openid(openid)
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

    model.insert_user(name, openid)

    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
@authenticated
def index():
    if request.method == 'POST':
        match_id = request.values.get('match-id')
        new_choice = request.values.get('bet-choice')
        model.update_match_gamblers(match_id, new_choice, g.me)

    matches = model.find_matches(reverse=True)
    return render_template('index.html', matches=matches[:app.config['MAX_MATCH_DISPLAY']])


@app.route('/board', methods=['GET'])
@authenticated
def board():
    many_series = model.generate_series()

    match_ids = many_series and many_series[0].points.keys() or []
    labels = ['{1} vs {2}'.format(*match_id.split('-')) for match_id in sorted(match_ids)]  # 用 sorted() 确保 match_ids 有序

    datasets = []
    for i, series in enumerate(many_series):
        s, l = (50, 50) if (i % 2) else (100, 70)
        color = 'hsl({h}, {s}%, {l}%)'.format(h=int(360 / len(many_series) * i), s=s, l=l)
        datasets.append(dict(label=series.gambler, data=list(series.points.values()),
                             borderColor=color, backgroundColor=color))

    # 插入初始 0 值
    labels.insert(0, '')
    for d in datasets:
        d['data'].insert(0, 0)

    data = dict()
    data['labels'] = labels
    data['datasets'] = datasets

    return render_template('board.html', label_count=len(labels), data=data)


@app.route('/rule', methods=['GET'])
@authenticated
def rule():
    return render_template('rule.html')
