# coding: utf-8

import os


SECRET_KEY = os.getenv('SECRET_KEY', 'super secret key')

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_LOGINDB = os.getenv('MONGO_LOGINDB', 'logins')
MONGO_TOURNAMENTDB = os.getenv('MONGO_TOURNAMENTDB', 'worldcup2018')
WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', '')

# TODO: REQUIRED_GAMBLERS's key should be ordered, so [-1] is always the latest tournament
REQUIRED_GAMBLERS = {
    'worldcup2018': ['大B', '金帝', '老套', '小白', '老排', '大钻', '李琛', '老大', '老娘', '汉姆'],
#    'eurocup2016' : ['大B', '老套', '小白', '老排', '大钻', '李琛', '老大', '老娘'],
}