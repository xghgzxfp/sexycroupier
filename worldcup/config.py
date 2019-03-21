# coding: utf-8

import os
from collections import namedtuple

Tournament = namedtuple('Tournament', ['dbname', 'league', 'display'])

SECRET_KEY = os.getenv('SECRET_KEY', 'super secret key')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_LOGINDB = os.getenv('MONGO_LOGINDB', 'logins')

WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')


TOURNAMENTS = [
    Tournament('eurocup2016', '欧国杯', '2016 欧洲杯'),
    Tournament('worldcup2018', '世界杯', '2018 世界杯'),
    Tournament('championsleague20182019', '欧联', '2018-2019 欧洲冠军联赛'),
]

DEFAULT_TOURNAMENT = TOURNAMENTS[-2]