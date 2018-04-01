# coding: utf-8

from collections import namedtuple
from datetime import datetime
from typing import List, Dict

from .app import db
from .constant import HANDICAP_DICT


# class Gambler:
#     name = "gambler's name"
#     openid = 'wechat openid'

Gambler = namedtuple('Gambler', ['name', 'openid'])


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


class Auction:
    cup = '2018-world-cup'
    team = 'england'
    gambler = "gambler's name"
    price = 23


def insert_auction(cup, team, gambler, price): return
def find_auction(cup, team): return


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
            score=float(score_a) if score_a != '' else None,
            gamblers=[]
        )
        self.b = dict(
            team=team_b,
            premium=float(premium_b),
            score=float(score_b) if score_b != '' else None,
            gamblers=[]
        )
        self.result = None

    def update_profit_and_loss_result(self):
        if self.a['score'] is None or self.b['score'] is None:
            return
        asc, bsc = self.a['score'], self.b['score']
        self.result = dict([(gambler, 0) for gambler in self.a['gamblers'] + self.b['gamblers']])
        for handicap in self.handicap:
            if asc > bsc + handicap:
                winner, loser = self.a, self.b
            elif asc < bsc + handicap:
                winner, loser = self.b, self.a
            else:
                continue
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

    def get_profit_and_loss_result(self):
        assert self.result is not None
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
        return
    db.match.insert(new_match.__dict__)
    return new_match


def update_match_score(match_time, team_a, team_b, score_a, score_b):
    match_id = generate_match_id(match_time, team_a, team_b)
    if score_a == '' or score_b == '':
        return
    db.match.update(
        {"id": match_id},
        {"$set": {"a.score": int(score_a), "b.score": int(score_b)}}
    )
    return


def update_match_handicap(match_time, team_a, team_b, handicap_display):
    match_id = generate_match_id(match_time, team_a, team_b)
    db.match.update(
        {"id": match_id},
        {"$set": {"handicap": generate_handicap_pair(handicap_display)}}
    )
    return


def update_match_gamblers(matchid, team, gambler):
    """Update betting decision in database

    """
    list_out = ("a" if team == "b" else "b") + ".gamblers"
    list_in = team + '.gamblers'
    return db.match.update({"id": matchid}, {"$pull": {list_out: gambler}, "$addToSet": {list_in: gambler}})


def update_match_weight(match_time, team_a, team_b, weight):
    match_id = generate_match_id(match_time, team_a, team_b)
    db.match.update(
        {"id": match_id},
        {"$set": {"weight": float(weight)}}
    )
    return


def find_matches(cup):
    return list(map(lambda x: Match(**x), db.match.find({'league': cup}).sort('id')))


class Series:
    '''
    cup = '2018-world-cup'
    gambler = 'name1'
    points = dict([
        ('201806010100-法国-西班牙', 17),
        ('201806010330-英格兰-德国', 15),
    ])
    '''
    def __init__(self, cup, gambler):
        self.cup = cup
        self.gambler = gambler
        self.latest_score = 0
        self.points = dict()

    def add_a_point(self, match):
        result = match.get_profit_and_loss_result()
        if self.gambler in result:
            self.latest_score += result[self.gambler]
        self.points[match.id] = self.latest_score


def generate_series(cup: str) -> Dict[str, List[Series]]:
    matches = find_matches(cup)
    gamblers = find_gamblers()
    gamblers_series = dict([(gambler, Series(cup, gambler)) for gambler in gamblers])
    for match in matches:
        match.update_profit_and_loss_result()
        for gambler_series in gamblers_series.values():
            gambler_series.add_a_point(match)
    return gamblers_series


if __name__ == "__main__":
    #insert_match('意甲', datetime(2018, 3, 31, 18, 30), '受半球/一球', '博洛尼亚', '罗马', '1.98', '1.88', '', '')
    update_match_score(datetime(2018, 3, 31, 18, 30), '博洛尼亚', '罗马', '0', '0')
