# coding: utf-8

import os
from collections import namedtuple

Tournament = namedtuple('Tournament', ['dbname', 'league', 'display', 'weight_schedule'])

SECRET_KEY = os.getenv('SECRET_KEY', 'super secret key')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_LOGINDB = os.getenv('MONGO_LOGINDB', 'logins')

WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')


TOURNAMENTS = [
    Tournament(dbname='eurocup2016',
               league='欧国杯',
               display='2016 欧洲杯',
               weight_schedule=[2 for i in range(36)] + [4 for i in range(8)] + [6 for i in range(4)] + [8, 8, 10]),
    Tournament(dbname='worldcup2018',
               league='世界杯',
               display='2018 世界杯',
               weight_schedule=[2 for i in range(56)] + [4 for i in range(4)] + [8, 8, 16, 16]),
    Tournament(dbname='championsleague20182019',
               league='欧联',
               display='18-19 欧冠',
               weight_schedule=[20 for i in range(8)] + [25 for i in range(4)] + [60]),
]

DEFAULT_TOURNAMENT = TOURNAMENTS[-2]

MAX_MATCH_DISPLAY = 20