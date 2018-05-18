# coding: utf-8


from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
from typing import List, Dict
from functools import lru_cache

from worldcup.app import db
from worldcup.constant import HANDICAP_DICT
import logging

# class Gambler:
#     name = "gambler's name"
#     openid = 'wechat openid'

Gambler = namedtuple('Gambler', ['name', 'openid'])

def utc_to_beijing(utc_time):
    return datetime.fromtimestamp(utc_time.timestamp() + 8 * 3600)


def beijing_to_utc(beijing_time):
    return datetime.fromtimestamp(beijing_time.timestamp() - 8 * 3600)


def cutofftime_handicap(match_time):
    # cutofftime_handicap is the time after which handicap will not change
    res = datetime(match_time.year, match_time.month, match_time.day, 12, 0, 0)
    if res >= match_time:
        res -= timedelta(1)
    return res


def cutofftime_bet(match_time):
    # cutofftime is the time during which bet is allowed fot the match
    st = cutofftime_handicap(match_time)
    ed = match_time
    return (st, ed)

def find_match_time_by_match_id(match_id):
    return db.match.find_one({'id': match_id})['match_time']


def insert_gambler(name: str, openid: str) -> Gambler:
    """根据 openid 创建 gambler"""
    gambler = Gambler(name=name, openid=openid)
    # 用 replace_one(upsert=True) 避免插入重复记录
    db.gambler.replace_one({'openid': openid}, gambler._asdict(), upsert=True)
    return gambler


def find_gambler_by_openid(openid: str) -> Gambler:
    """根据 openid 获取 gambler"""
    d = db.gambler.find_one({'openid': openid})
    if not d:
        return
    return Gambler(name=d['name'], openid=d['openid'])


def find_gamblers() -> List[Gambler]:
    """获取全部 gambler"""
    return [Gambler(name=d['name'], openid=d['openid']) for d in db.gambler.find().sort('name') if d]

def find_required_gamblers() -> List[Gambler]:
    from .config import REQUIRED_GAMBLERS
    return list(filter(lambda x: x.name in REQUIRED_GAMBLERS, find_gamblers()))

'''
class Auction:
    cup = '2018-world-cup'
    team = 'england'
    gambler = "gambler's name"
    price = 23
'''    
Auction = namedtuple('Auction', ['cup', 'team', 'gambler', 'price'])


def insert_auction(cup, team, gambler, price):
    auction = Auction(cup=cup, team=team, gambler=gambler, price=price)
    db.auction.replace_one({'cup': cup, 'team': team}, auction._asdict(), upsert=True)
    return auction

def find_auction(cup, team): 
    a = db.auction.find_one({'cup': cup, 'team': team})
    if not a:
        return None
    return Auction(cup=a['cup'], team=a['team'], gambler=a['gambler'], price=a['price'])

# @lru_cache(maxsize=32)
def get_team_gambler_in_auctions(cup, team):
    a = find_auction(cup, team)
    if a is None:
        return None
    return a.gambler

class Match:
    '''
    id = None   # <%Y%m%d%H%M>-<team-a>-<team-b>
    league = None
    match_time = None
    handicap_display = None
    a = dict(
        team=None,
        premium=None,
        score=None,
        gamblers=[],
    )
    b = dict(
        team=None,
        premium=None,
        score=None, 
        gamblers=[],
    )
    handicap = (None, None)
    weight = None
    '''
    def __init__(self, *args, **kwargs):
        if 'id' in kwargs:
            self.__dict__ = kwargs
            return
        league_name, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b = args
        assert all(map(lambda x: x is not None, args))
        if 'weight' in kwargs:
            self.weight = kwargs['weight']
        else:
            self.weight = 2
        self.id = generate_match_id(match_time, team_a, team_b)
        self.league = league_name
        self.match_time = match_time
        self.handicap_display = handicap_display

        self.handicap = generate_handicap_pair(handicap_display)
        self.a = dict(
            team=team_a,
            premium=float(premium_a),
            score=int(score_a) if score_a != '' else None,
            gamblers=[]
        )
        self.b = dict(
            team=team_b,
            premium=float(premium_b),
            score=int(score_b) if score_b != '' else None,
            gamblers=[]
        )
        self.result = None

    def completed(self) -> bool:
        if self.a['score'] is None or self.b['score'] is None:
            return False
        else:
            return True

    def update_profit_and_loss_result(self, required_gamblers=None) -> int:
        if not self.completed():
            return
        asc, bsc = self.a['score'], self.b['score']
        if required_gamblers is None:
            required_gamblers = []
        else:
            required_gamblers = list(map(lambda x: x.name, required_gamblers))
        self.result = dict([(gambler, 0) 
            for gambler in self.a['gamblers'] + self.b['gamblers'] + required_gamblers])
        for handicap in self.handicap:
            if asc > bsc + handicap:
                winner, loser = self.a, self.b
            elif asc < bsc + handicap:
                winner, loser = self.b, self.a
            else:
                continue
            for gambler in required_gamblers:
                if gambler not in self.a['gamblers'] and gambler not in self.b['gamblers']:
                    loser['gamblers'].append(gambler)
            stack = self.weight / len(self.handicap)
            reward_sum = stack * len(loser['gamblers'])
            if len(winner['gamblers']) > 0:
                winner_reward = reward_sum / len(winner['gamblers'])
            else:
                winner_reward = 0
            for gambler in loser['gamblers']:
                self.result[gambler] -= stack
            for gambler in winner['gamblers']:
                self.result[gambler] += winner_reward
            winner_team_gambler = get_team_gambler_in_auctions(self.league, winner['team'])
            loser_team_gambler = get_team_gambler_in_auctions(self.league, loser['team'])
            if winner_team_gambler in winner['gamblers']:
                self.result[winner_team_gambler] += winner_reward
            if loser_team_gambler in winner['gamblers']:
                self.result[loser_team_gambler] += winner_reward

    def get_profit_and_loss_result(self):
        if self.result is None:
            self.update_profit_and_loss_result()
        if not self.completed():
            logging.warning('try to get result of uncompleted match')
        return self.result

    def __str__(self):
        return str(self.__dict__)


def generate_match_id(match_time, team_a, team_b):
    res = match_time.strftime('%Y%m%d%H%M') + '-' + team_a + '-' + team_b
    return res


def generate_handicap_pair(handicap_display):
    if handicap_display[0] == '受':
        sign = -1
        handicap_display = handicap_display[1:]
    else:
        sign = 1

    handicaps = handicap_display.split('/')
    if len(handicaps) == 1:
        return sign * HANDICAP_DICT[handicaps[0]], sign * HANDICAP_DICT[handicaps[0]]
    else:
        return sign * HANDICAP_DICT[handicaps[0]], sign * HANDICAP_DICT[handicaps[1]]


def insert_match(league_name, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b):
    new_match = Match(league_name, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b)
    # do nothing if duplicate
    if db.match.find({"id": new_match.id}).limit(1).count():
        return new_match
    db.match.insert(new_match.__dict__)
    logging.info(new_match.id + ' is inserted')
    return new_match


def update_match_score(match_time, team_a, team_b, score_a, score_b):
    match_id = generate_match_id(match_time, team_a, team_b)
    if score_a == None or score_b == None:
        return
    db.match.update(
        {"id": match_id},
        {"$set": {"a.score": score_a, "b.score": score_b}}
    )
    logging.info(match_id + ' score updated as ' + str(score_a) + ':' + str(score_b))
    return


def update_match_handicap(match_time, team_a, team_b, handicap_display):
    match_id = generate_match_id(match_time, team_a, team_b)
    db.match.update(
        {"id": match_id},
        {"$set": {"handicap": generate_handicap_pair(handicap_display)}}
    )
    logging.info(match_id + ' handicap updated as ' + handicap_display)
    return


def update_match_gamblers(match_id, team, gambler):
    """Update betting decision in database

    """
    list_out = ("a" if team == "b" else "b") + ".gamblers"
    list_in = team + '.gamblers'
    return db.match.update({"id": match_id}, {"$pull": {list_out: gambler}, "$addToSet": {list_in: gambler}})


def update_match_gamblers_check_bet_time(match_id, team, gambler):
    st, ed = cutofftime_bet(find_match_time_by_match_id(match_id))
    current_time = datetime.utcnow()
    current_beijing_time = utc_to_beijing(current_time)
    if st < current_beijing_time <= ed:
        update_match_gamblers(match_id, team, gambler)


def update_match_weight(match_time, team_a, team_b, weight):
    match_id = generate_match_id(match_time, team_a, team_b)
    db.match.update(
        {"id": match_id},
        {"$set": {"weight": float(weight)}}
    )
    return


def find_matches(cup):
    return list(map(lambda x: Match(**x), db.match.find({'league': cup}).sort('id')))

def find_matches_display(cup):
    ret = find_matches(cup)
    return reversed(ret)


class Series:
    '''
    cup = '2018-world-cup'
    gambler = 'name1'
    points = dict([
        ('201806010100-法国-西班牙', 17),
        ('201806010330-英格兰-德国', 15),
    ])
    '''
    def __init__(self, cup, gambler_name):
        self.cup = cup
        self.gambler = gambler_name
        self.latest_score = 0
        self.points = OrderedDict()

    def add_a_point(self, match):
        result = match.get_profit_and_loss_result()
        if self.gambler in result:
            self.latest_score += result[self.gambler]
        self.points[match.id] = self.latest_score


def generate_series(cup: str) -> Dict[str, Series]:
    matches = find_matches(cup)
    Gamblers = find_gamblers()
    gambler_names = [G.name for G in Gamblers]
    gamblers_series = dict([(gambler_name, Series(cup, gambler_name)) for gambler_name in gambler_names])
    required_gamblers = find_required_gamblers()
    for match in matches:
        if match.completed():
            match.update_profit_and_loss_result(required_gamblers)
            for gambler_series in gamblers_series.values():
                gambler_series.add_a_point(match)
    return gamblers_series


def match_id_to_diplay(match_id : str):
    parsed = match_id.split('-')
    return parsed[-2] + " vs " + parsed[-1]


if __name__ == "__main__":
    #insert_match('意甲', datetime(2018, 3, 31, 18, 30), '受半球/一球', '博洛尼亚', '罗马', '1.98', '1.88', '', '')
    update_match_score(datetime(2018, 3, 31, 18, 30), '博洛尼亚', '罗马', '0', '0')
