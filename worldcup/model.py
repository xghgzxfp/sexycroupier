# coding: utf-8

from worldcup.app import db
from worldcup.constant import handicap_dic
from datetime import datetime

class Gambler:
    id = "gambler's name"
    openid = 'wechat openid'


def insert_gambler(name, openid): return
def find_gambler_by_openid(openid): return
def find_gamblers(): return


class Auction:
    cup = '2018-world-cup'
    team = 'england'
    gambler = "gambler's name"
    price = 23


def insert_auction(cup, team, gambler, price): return
def find_auction(cup, team): return


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
        return [sign * handicap_dic[handicaps[0]], sign * handicap_dic[handicaps[0]]]
    else:
        return [sign * handicap_dic[handicaps[0]], sign * handicap_dic[handicaps[1]]]


class Match:
    '''
    id = None   # <%Y%m%d%H%M>-<team-a>-<team-b>
    league = None
    match_time = None
    handicap_display = None
    a = dict(
        team=None,
        handicap=None,
        premium=None,
        score=None,
        gamblers=[],
    )
    b = dict(
        team=None,
        handicap=None,
        premium=None,
        score=None,
        gamblers=[],
    )
    weight = None
    '''
    def __init__(self, league_name, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b, weight=2):
        self.id = generate_match_id(match_time, team_a, team_b)
        self.league = league_name
        self.match_time = match_time
        self.handicap_display = handicap_display

        handicaps = generate_handicap_pair(handicap_display)
        self.a = dict(
            team=team_a,
            handicap=float(handicaps[0]),
            premium=float(premium_a),
            score=float(score_a) if score_a != '' else None
        )
        self.b = dict(
            team=team_b,
            handicap=float(handicaps[1]),
            premium=float(premium_b),
            score=float(score_b) if score_b != '' else None
        )
        self.weight = weight

    def __str__(self):
        print('id: ', self.id)
        print('league: ', self.league)
        print('match_time: ', self.match_time)
        print('handicap_display: ', self.handicap_display)
        print(self.a)
        print(self.b)
        print('weight: ', self.weight)
        return ""



def insert_match(match):
    if db.match.find({"id" : match.id}).limit(1).count() > 0:
        return


    return



def update_match_handicap(matchid, a, b): return

def update_match_gamblers(matchid, team, gambler):
    """Update betting decision in database

    """

    list_out = ("a" if team == "b" else "b") + ".player"
    list_in = team + '.player'

    return db.match.update({"id" : matchid}, {"$pull"      : { list_out : gambler}, "$addToSet"  : { list_in : gambler}})


def update_match_score(match, a, b): return
def update_match_weight(match, weight): return
def find_matches(cup): return


class Series:
    cup = '2018-world-cup'
    gambler = 'name1'
    points = dict([
        ('2018060101-france-spain', 17),
        ('2018060103-england-germany', 15),
    ])


def generate_series(cup): return


if __name__ == "__main__":
    temp1 = Match('意甲', datetime(2018, 3, 31, 18, 30), '受半球/一球', '博洛尼亚', '罗马', '1.98', '1.88', '', '')
    temp2 = Match('意甲', datetime(2018, 3, 31, 21, 0), '一球/球半', '亚特兰大', '乌迪内斯', '2', '1.86', '', '')
    #temp3 = Match('意甲', datetime(2018, 3, 31, 21, 0), '受平手/半球', '卡利亚里', '都灵', '1.78', '2.08', '', '')
    #temp4 = Match('意甲', datetime(2018, 3, 31, 21, 0), '一球', '佛罗伦萨', '克罗托内', '1.8', '2.06', '', '')

    print(temp1)
    print(temp2)
    #print(temp3)
    #print(temp4)