# coding: utf-8

import datetime
import logging
import pymongo

from collections import namedtuple, OrderedDict
from typing import List, Optional
from .app import logindb, tournamentdb, config
from .constant import HANDICAP_DICT


def utc_to_beijing(utc_time: datetime.datetime) -> datetime.datetime:
    return utc_time + datetime.timedelta(hours=8)


# class Gambler:
#     name = "gambler's name"
#     openid = 'wechat openid'

User = namedtuple('User', ['name', 'openid'])


def insert_gambler(name: str, openid: str) -> User:
    """根据 openid 创建 gambler"""
    user = User(name=name, openid=openid)
    # 用 replace_one(upsert=True) 避免插入重复记录
    logindb.user.replace_one({'openid': openid}, user._asdict(), upsert=True)
    return user


def drop_user(ident: str):
    """根据 name / openid 删除 gambler"""
    user = find_user_by_name(ident) or find_user_by_openid(ident)
    if not user:
        return
    # user
    logindb.gambler.delete_one({'name': user.name, 'openid': user.openid})
    # TODO: drop should be done in all tournament dbs
    # match
    # tournamentdb.match.update_many({}, {'$pull': {'a.gamblers': user.name, 'b.gamblers': user.name}})
    # auction
    # 不删除 auction 以免丢失交易记录


def update_user_name(current: str, new: str):
    """重命名 user"""
    # gambler
    logindb.user.update_one({'name': current}, {'$set': {'name': new}})
    # TODO: update all tournament dbs' match and auction with new gambler name
    #for tournament_str in config.REQUIRED_GAMBLERS.keys():
    #    tournamentdb=MongoClient(config['MONGO_URI'])[tournament_str]
    #    tournamentdb.match.update_many({'a.gamblers': current}, {'$set': {'a.gamblers.$': new}})
    #    tournamentdb.match.update_many({'b.gamblers': current}, {'$set': {'b.gamblers.$': new}})
    #    tournamentdb.auction.update_many({'gambler': current}, {'$set': {'gambler': new}})

def find_user_by_name(name: str) -> Optional[User]:
    """根据 name 获取 user"""
    d = logindb.user.find_one({'name': name})
    if not d:
        return
    return User(name=d['name'], openid=d['openid'])


def find_user_by_openid(openid: str) -> Optional[User]:
    """根据 openid 获取 user"""
    d = logindb.user.find_one({'openid': openid})
    if not d:
        return
    return User(name=d['name'], openid=d['openid'])


def find_gamblers() -> List[User]:
    """获取全部 gambler"""
    return [find_user_by_name(gambler['name']) for gambler in tournamentdb.gambler.find()]


# class Auction:
#     cup = '2018-world-cup'
#     team = 'england'
#     gambler = "gambler's name"
#     price = 23
# TODO: remove cup from Auction
Auction = namedtuple('Auction', ['cup', 'team', 'gambler', 'price'])


def insert_auction(cup: str, team: str, gambler: str, price: int) -> Auction:
    """插入拍卖记录"""
    auction = Auction(cup=cup, team=team, gambler=gambler, price=price)
    tournamentdb.auction.replace_one({'cup': cup, 'team': team}, auction._asdict(), upsert=True)
    return auction


def find_auction(cup: str, team: str) -> Optional[Auction]:
    """根据 team 查找拍卖记录"""
    a = tournamentdb.auction.find_one({'cup': cup, 'team': team})
    if not a:
        return None
    return Auction(cup=a['cup'], team=a['team'], gambler=a['gambler'], price=a['price'])


def find_team_owner(cup: str, team: str) -> Optional[str]:
    """根据拍卖记录查找 team owner"""
    a = find_auction(cup, team)
    return a.gambler if a else None


# class Match
#     id = None   # <%Y%m%d%H%M>-<team-a>-<team-b>
#     league = None
#     match_time = None
#     handicap_display = None
#     a = dict(
#         team=None,
#         premium=None,
#         score=None,
#         gamblers=[],
#     )
#     b = dict(
#         team=None,
#         premium=None,
#         score=None,
#         gamblers=[],
#     )
#     handicap = (None, None)
#     weight = None

class Match:

    def __init__(self, league, match_time, handicap_display,
                 team_a, team_b, premium_a, premium_b, score_a, score_b,
                 weight=2, id=None):
        self.league = league

        self.match_time = match_time
        self.handicap_display = handicap_display
        self.handicap = _generate_handicap_pair(handicap_display)

        try:
            score_a = int(score_a)
            score_b = int(score_b)
        except Exception:
            score_a = None
            score_b = None

        self.a = dict(
            team=team_a,
            premium=float(premium_a),
            score=score_a,
            gamblers=[],
            owner=find_team_owner(cup=self.league, team=team_a),
        )
        self.b = dict(
            team=team_b,
            premium=float(premium_b),
            score=score_b,
            gamblers=[],
            owner=find_team_owner(cup=self.league, team=team_b),
        )

        self.weight = weight
        self.id = id or _generate_match_id(match_time, team_a, team_b)

        self._result = None

    def __eq__(self, other):
        return self._asdict() == other._asdict()

    @classmethod
    def from_mongo(cls, m: dict): # -> Optional[Match]
        """根据 mongo 返回的 record 构造 Match 对象"""
        if not m:
            return
        match = Match(league=m['league'], match_time=m['match_time'], handicap_display=m['handicap_display'],
                      team_a=m['a']['team'], premium_a=m['a']['premium'], score_a=m['a']['score'],
                      team_b=m['b']['team'], premium_b=m['b']['premium'], score_b=m['b']['score'],
                      weight=m['weight'], id=m['id'])
        match.a['gamblers'] = m['a']['gamblers']
        match.b['gamblers'] = m['b']['gamblers']
        return match

    @property
    def handicap_cutoff_time(self) -> datetime.datetime:
        """盘口截止时间 此时间后盘口不再变化"""
        cutoff_time = datetime.datetime(self.match_time.year, self.match_time.month, self.match_time.day, 12, 0, 0)
        if cutoff_time >= self.match_time:
            cutoff_time -= datetime.timedelta(days=1)
        return cutoff_time

    @property
    def bet_cutoff_time(self) -> datetime.datetime:
        """投注截止时间 此时间后无法再投注"""
        return self.match_time

    def _asdict(self) -> dict:
        """存入数据库的结构

        明确了哪些数据会被存入数据库持久化，而其他数据则只暂存在内存中
        """
        def _team_asdict(team: dict) -> dict:
            return dict(
                team=team['team'],
                premium=team['premium'],
                score=team['score'],
                gamblers=team['gamblers'],
            )
        return dict(
            league=self.league,
            match_time=self.match_time,
            handicap_display=self.handicap_display,
            handicap=self.handicap,
            a=_team_asdict(self.a),
            b=_team_asdict(self.b),
            weight=self.weight,
            id=self.id,
        )

    def can_bet(self) -> bool:
        """比赛是否可投注"""
        return self.handicap_cutoff_time < utc_to_beijing(datetime.datetime.utcnow()) <= self.bet_cutoff_time

    def can_update_handicap(self) -> bool:
        """比赛是否可更新盘口"""
        return utc_to_beijing(datetime.datetime.utcnow()) < self.handicap_cutoff_time

    def is_completed(self) -> bool:
        """比赛是否已结束"""
        if self.a['score'] is None or self.b['score'] is None:
            return False
        return True

    def is_loser(self, team) -> bool:
        if not self.is_completed():
            return False
        for handicap in self.handicap:
            if self.a['score'] > self.b['score'] + handicap:
                return team == self.b['team']
            if self.a['score'] < self.b['score'] + handicap:
                return team == self.a['team']
        return False

    def update_profit_and_loss_result(self, required_gamblers: List[User]) -> dict:
        if not self.is_completed():
            return
        asc, bsc = self.a['score'], self.b['score']
        if required_gamblers is None:
            required_gamblers = []
        else:
            required_gamblers = list(map(lambda x: x.name, required_gamblers))
        self._result = dict([(gambler, 0)
            for gambler in self.a['gamblers'] + self.b['gamblers'] + required_gamblers])
        for handicap in self.handicap:
            punish_gamblers = []
            for gambler in required_gamblers:
                if gambler not in self.a['gamblers'] and gambler not in self.b['gamblers']:
                    punish_gamblers.append(gambler)
            stack = self.weight / len(self.handicap)
            for gambler in punish_gamblers:
                self._result[gambler] -= stack

            if asc > bsc + handicap:
                winner, loser = self.a, self.b
            elif asc < bsc + handicap:
                winner, loser = self.b, self.a
            else:
                continue
            reward_sum = stack * (len(loser['gamblers']) + len(punish_gamblers))
            if len(winner['gamblers']) > 0:
                winner_reward = reward_sum / len(winner['gamblers'])
            else:
                winner_reward = 0
            for gambler in loser['gamblers']:
                self._result[gambler] -= stack
            for gambler in winner['gamblers']:
                self._result[gambler] += winner_reward
            winner_team_owner = find_team_owner(self.league, winner['team'])
            loser_team_owner = find_team_owner(self.league, loser['team'])
            if winner_team_owner in winner['gamblers']:
                self._result[winner_team_owner] += winner_reward
            if winner_team_owner != loser_team_owner and loser_team_owner in winner['gamblers']:
                self._result[loser_team_owner] += winner_reward

        return self._result

    def __repr__(self):
        return 'Match(id={}, score_a={}, score_b={})'.format(self.id, self.a['score'], self.b['score'])


def _generate_match_id(match_time, team_a, team_b):
    return match_time.strftime('%Y%m%d%H%M') + '-' + team_a + '-' + team_b


def _generate_handicap_pair(handicap_display):
    if handicap_display.startswith('受'):
        sign = -1
        handicap_display = handicap_display[1:]
    else:
        sign = 1

    handicaps = handicap_display.split('/')
    if len(handicaps) == 1:
        return sign * HANDICAP_DICT[handicaps[0]], sign * HANDICAP_DICT[handicaps[0]]
    else:
        return sign * HANDICAP_DICT[handicaps[0]], sign * HANDICAP_DICT[handicaps[1]]


def insert_match(league, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b, weight=2):
    """创建新比赛或返回已存在比赛"""
    # 如果 match 已存在则直接返回
    match = find_match_by_id(_generate_match_id(match_time, team_a, team_b))
    if match:
        logging.info('Existing match: match={}'.format(match.id))
        return match
    # 否则插入新 match
    match = Match(league, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b, weight)
    tournamentdb.match.insert_one(match._asdict())
    logging.info('New match: match={}'.format(match.id))
    return match


def update_match_score(match_id: str, score_a: str, score_b: str):
    """更新比分"""
    try:
        score_a = int(score_a)
        score_b = int(score_b)
    except Exception:
        return
    tournamentdb.match.update_one(
        {"id": match_id},
        {"$set": {"a.score": score_a, "b.score": score_b}}
    )
    logging.info('Score updated: match={} score="{}:{}"'.format(match_id, score_a, score_b))


def update_match_handicap(match_id: str, handicap_display: str, cutoff_check=True):
    """更新盘口"""
    match = find_match_by_id(match_id)
    # 若比赛不存在或当前盘口已定则直接返回
    if not match or (cutoff_check and not match.can_update_handicap()):
        return
    tournamentdb.match.update_one(
        {"id": match_id},
        {"$set": {"handicap": _generate_handicap_pair(handicap_display), "handicap_display": handicap_display}}
    )
    logging.info('Handicap updated: match={} handicap="{}"'.format(match_id, handicap_display))


def update_match_gamblers(match_id, team, gambler, cutoff_check=True):
    """更新投注结果"""
    match = find_match_by_id(match_id)
    # 若比赛不存在或当前非投注时间则直接返回
    if not match or (cutoff_check and not match.can_bet()):
        return
    list_out = ("a" if team == "b" else "b") + ".gamblers"
    list_in = team + '.gamblers'
    return tournamentdb.match.update_one({"id": match_id}, {"$pull": {list_out: gambler}, "$addToSet": {list_in: gambler}})


def update_match_weight(match_id, weight):
    """更新本场赌注"""
    tournamentdb.match.update_one(
        {"id": match_id},
        {"$set": {"weight": float(weight)}}
    )


def update_match_time(match_id: str, match_time: datetime.datetime):
    """更新比赛时间

    id 由 match_time 生成 两个字段需同时更新
    """
    match = find_match_by_id(match_id)
    if not match:
        return
    tournamentdb.match.update_one(
        {"id": match_id},
        {"$set": {"id": _generate_match_id(match_time, match.a['team'], match.b['team']), "match_time": match_time}}
    )


def find_matches(reverse=False) -> List[Match]:
    """返回所有比赛 默认为 id 升序"""
    direction = pymongo.DESCENDING if reverse else pymongo.ASCENDING
    return [Match.from_mongo(m) for m in tournamentdb.match.find().sort('id', direction=direction)]


def find_match_by_id(match_id: str) -> Optional[Match]:
    """根据 ID 返回比赛 找不到时返回 None"""
    return Match.from_mongo(tournamentdb.match.find_one({'id': match_id}))


# class Series:
#     gambler = 'name1'
#     points = OrderedDict([
#         ('201806010100-法国-西班牙', 17),
#         ('201806010330-英格兰-德国', 15),
#     ])

class Series:

    def __init__(self, gambler: str, matches: list, required_gamblers: List[User]):
        self.gambler = gambler
        self.points = OrderedDict()
        self._add_matches(matches, required_gamblers)

    def _add_matches(self, matches: list, required_gamblers: List[User]):
        latest = 0
        for match in sorted(matches, key=lambda m: m.match_time):
            if not match.is_completed():
                continue
            result = match.update_profit_and_loss_result(required_gamblers=required_gamblers)
            latest += result and result.get(self.gambler) or 0
            self.points[match.id] = latest


def generate_series() -> List[Series]:
    gamblers = find_gamblers()
    matches = find_matches()
    return [Series(gambler.name, matches, gamblers) for gambler in gamblers]
