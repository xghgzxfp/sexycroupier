# coding: utf-8

import datetime
import os
from collections import namedtuple


Tournament = namedtuple('Tournament', ['dbname', 'league', 'display', 'weight_schedule'])


SECRET_KEY = os.getenv('SECRET_KEY', 'super secret key')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_LOGINDB = os.getenv('MONGO_LOGINDB', 'logins')

WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')

# weight schedule 应为 北京时间 比赛日+1
TOURNAMENTS = [
    Tournament(
        dbname='eurocup2016',
        league='欧国杯',
        display='2016 欧洲杯',
        weight_schedule=[
            (datetime.datetime(2016, 6, 23), 2),    # group games and 1/8 final
            (datetime.datetime(2016, 6, 28), 4),    # group games and 1/8 final
            (datetime.datetime(2016, 7, 4), 6),     # 1/4 final
            (datetime.datetime(2016, 7, 8), 8),     # semi final
            (datetime.datetime(2016, 7, 11), 10),   # final
        ],
    ),
    Tournament(
        dbname='2018-international-friendlies',
        league='国友赛',
        display='2018 国友赛',
        weight_schedule=[ ],
    ),
    Tournament(
        dbname='worldcup2018',
        league='世界杯',
        display='2018 世界杯',
        weight_schedule=[
            (datetime.datetime(2018, 7, 5), 2),     # group games + 1/8 final
            (datetime.datetime(2018, 7, 9), 4),     # 1/4 final
            (datetime.datetime(2018, 7, 13), 8),    # semi final
            (datetime.datetime(2018, 7, 16), 16),   # final + 3rd playoff
        ],
    ),
    Tournament(
        dbname='championsleague20182019',
        league='欧联',
        display='18-19 欧冠',
        weight_schedule=[
            (datetime.datetime(2019, 4, 19), 4),    # 1/4 final
            (datetime.datetime(2019, 5, 10), 8),    # semi final
            (datetime.datetime(2019, 6, 3), 16),    # final + 3rd playoff
        ],
    ),
    Tournament(
        dbname='worldcup2022',
        league='世界盃',
        display='2022 世界杯',
        weight_schedule=[
            (datetime.datetime(2022, 12, 8), 2),    # group games + 1/8 final
            (datetime.datetime(2022, 12, 13), 4),   # 1/4 final
            (datetime.datetime(2022, 12, 16), 8),   # semi final
            (datetime.datetime(2022, 12, 19), 16),  # final + 3rd playoff
        ],
    ),
    Tournament(
        dbname='eurocup2024',
        league='欧国杯',
        display='2024 欧洲杯',
        weight_schedule=[
            (datetime.datetime(2024, 7, 4), 2),     # 1/8 final
            (datetime.datetime(2024, 7, 8), 4),     # 1/4 final
            (datetime.datetime(2024, 7, 12), 8),    # semi final
            (datetime.datetime(2024, 7, 16), 16),   # final + 3rd playoff
        ],
    ),
]

DEFAULT_TOURNAMENT = TOURNAMENTS[-1]

MAX_MATCH_DISPLAY = 20
