# coding: utf-8

from worldcup.app import db


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


class Match:
    id = '2018060103-england-germany'   # <%Y%m%d%H>-<team-a>-<team-b>
    cup = '2018-world-cup'
    a = dict(
        team='england',
        handicap=0.5,
        score=2,
        gamblers=['name1', 'name2'],
    )
    b = dict(
        team='germany',
        handicap=0.5,
        score=3,
        gamblers=['name3', 'name4'],
    )
    weight = 2


def insert_match(cup, a, b): return
def update_match_handicap(match, a, b): return

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
