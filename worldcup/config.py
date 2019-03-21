# coding: utf-8

import os
from collections import namedtuple

Tournament = namedtuple('Tournament', ['dbname', 'league'])

SECRET_KEY = os.getenv('SECRET_KEY', 'super secret key')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_LOGINDB = os.getenv('MONGO_LOGINDB', 'logins')

WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')

DEFAULT_TOURNAMENT = Tournament('worldcup2018', '世界杯')

TOURNAMENTS = [
    Tournament('eurocup2016', '欧国杯'),
    Tournament('worldcup2018', '世界杯'),
    Tournament('championsleague20182019', '欧联'),
]