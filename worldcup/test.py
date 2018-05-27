import pytest

from worldcup.app import db
from worldcup import match_getter
from worldcup import model
import datetime
import json
import os


test_names = ['bigzuan', 'midzuan', 'smallzuan', 'minizuan']
test_gamblers_choice = [
    ['a', 'a', 'a', 'a'],
    ['a', 'b', 'a', 'b'],
    ['b', 'b', 'b', 'b'],
    ['b', 'a', 'a', 'a']
]

test_matches = [
    ['硬糙', datetime.datetime(2018, 3, 31, 19, 30), '受一球', '水宫', '利浦', '2.08', '1.78', '2', '4'],
    ['硬糙', datetime.datetime(2018, 3, 31, 22, 0), '平手', '白顿', '莱特城', '2.02', '1.84', '3', '3'],
    ['硬糙', datetime.datetime(2018, 3, 31, 22, 10), '球半', '曼特联', '斯西', '1.78', '2.08', '1', '1'],
    ['硬糙', datetime.datetime(2018, 3, 31, 22, 10), '半球/一球', '纽尔联', '哈尔德', '2.02', '1.84', '2', '1'],
]

test_cup = '硬糙'

test_result = {
    'bigzuan': [-2, -2, -4, -3],
    'midzuan': [-2, -2, -4, -5],
    'smallzuan': [2, 2, 8, 7],
    'minizuan': [2, 2, 0, 1],
}

test_result_with_auctions = {
    'bigzuan': [-2, -2, -4, -2],
    'midzuan': [-2, -2, -4, -5],
    'smallzuan': [2, 2, 14, 13],
    'minizuan': [2, 2, 0, 2],
}

test_auctions = [
    ('水宫', 'bigzuan', 12),
    ('利浦', 'midzuan', 21),
    ('白顿', 'smallzuan', 32),
    ('莱特城', 'minizuan', 1),
    ('曼特联', 'smallzuan', 3),
    ('斯西', 'midzuan', 4),
    ('纽尔联', 'bigzuan', 6),
    ('哈尔德', 'minizuan', 123),
]


def add_user():
    for name in test_names:
        db.gambler.insert_one({'name': name, 'openid': name})


def del_user():
    for name in test_names:
        if db.gambler.find({"name": name}).count() >= 1:
            db.gambler.delete_many({'name': name})


def load_data(cup, filename):
    file_path = os.path.join(os.path.dirname(__file__), 'test_data', cup, filename)
    return json.load(open(file_path, 'r'))


def load_users(cup):
    gamblers = load_data(cup, 'players.json')
    for gambler in gamblers.keys():
        model.insert_gambler(gambler, gambler + '_openid')
    return len(gamblers)


def del_loaded_users(cup):
    gamblers = load_data(cup, 'players.json')
    for gambler in gamblers.keys():
        db.gambler.delete_many({'openid': gambler + '_openid'})


def insert_test_matches():
    for mch in test_matches:
        match_getter.insert_match(*mch)


def del_test_matches():
    matches = map(lambda x: model.Match(*x), test_matches)
    for m in matches:
        if db.match.find({'id': m.id}).count() >= 1:
            db.match.delete_many({'id': m.id})


def users_choose_teams():
    matche_ids = list(map(lambda x: model.Match(*x).id, test_matches))
    for name, choice in zip(test_names, test_gamblers_choice):
        for a_id, team in zip(matche_ids, choice):
            model.update_match_gamblers(a_id, team, name, cutoff_check=False)


def insert_auctions():
    for auc in test_auctions:
        model.insert_auction(test_cup, *auc)


def delete_auctions():
    for auc in test_auctions:
        db.auction.delete_many({'cup': test_cup, 'team': auc[0]})


def test_add_user():
    del_user()
    cnt = db.gambler.find().count()
    add_user()
    assert db.gambler.find().count() == cnt + len(test_names)


def test_del_user():
    del_user()
    add_user()
    cnt = db.gambler.find().count()
    del_user()
    assert db.gambler.find().count() == cnt - len(test_names)


def test_load_users():
    cup = 'E_Cup'
    del_loaded_users(cup)
    cnt = db.gambler.find().count()
    n = load_users(cup)
    assert db.gambler.find().count() == cnt + n
    del_loaded_users(cup)
    assert db.gambler.find().count() == cnt


def test_insert_matches():
    del_test_matches()
    cnt = db.match.find().count()
    insert_test_matches()
    assert db.match.find().count() == cnt + len(test_matches)
    insert_test_matches()
    assert db.match.find().count() == cnt + len(test_matches)
    del_test_matches()
    assert db.match.find().count() == cnt


def test_insert_auctions():
    delete_auctions()
    cnt = db.auction.find().count()
    insert_auctions()
    assert db.auction.find().count() == cnt + len(test_auctions)
    delete_auctions()


def test_gamblers_choose_teams():
    del_test_matches()
    insert_test_matches()
    matche_ids = list(map(lambda x: model.Match(*x).id, test_matches))
    for a_id in matche_ids:
        assert db.match.find({'id': a_id}).count() == 1
    users_choose_teams()
    op = {
        'a': 'b',
        'b': 'a',
    }
    for name, choice in zip(test_names, test_gamblers_choice):
        for a_id, team in zip(matche_ids, choice):
            assert name in db.match.find_one({'id': a_id})[team]['gamblers']
            assert name not in db.match.find_one({'id': a_id})[op[team]]['gamblers']
    del_test_matches()


def test_find_matches():
    del_test_matches()
    insert_test_matches()
    matches = model.find_matches(test_cup)
    assert len(matches) == len(test_matches)


def test_result_correctness():
    del_test_matches()
    insert_test_matches()
    del_user()
    add_user()
    users_choose_teams()
    many_series = model.generate_series(test_cup)
    cnt = 0
    for series in many_series:
        if series.gambler not in test_result:
            continue
        cnt += 1
        assert list(series.points.values()) == test_result[series.gambler]
    assert cnt == len(test_result)
    del_user()
    del_test_matches()


def test_result_correctness_with_auctions():
    del_test_matches()
    insert_test_matches()
    del_user()
    add_user()
    users_choose_teams()
    insert_auctions()
    many_series = model.generate_series(test_cup)
    cnt = 0
    for series in many_series:
        if series.gambler not in test_result_with_auctions:
            continue
        cnt += 1
        assert list(series.points.values()) == test_result_with_auctions[series.gambler]
    assert cnt == len(test_result_with_auctions)
    del_user()
    del_test_matches()
    delete_auctions()
