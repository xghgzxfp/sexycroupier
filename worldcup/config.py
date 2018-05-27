# coding: utf-8

import os


SECRET_KEY = os.getenv('SECRET_KEY', 'super secret key')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DBNAME = os.getenv('MONGO_DBNAME', 'worldcup')

WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')

LEAGUE_NAME = '英超'

