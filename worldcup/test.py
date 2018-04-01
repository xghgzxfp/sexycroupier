import pytest

from worldcup.app import db
from worldcup import match_getter
from worldcup import model
import datetime

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
    'bigzuan': -3,
    'midzuan': -5,
    'smallzuan': 7,
    'minizuan': 1
}

def add_user():
    for name in test_names:
        db.users.insert_one({'username': name, 'password': name})


def del_user():
    for name in test_names:
        if db.users.find({"username": name}).count() >= 1:
            db.users.delete_many({'username': name})


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
            model.update_match_gamblers(a_id, team, name)


def test_add_user():
    del_user()
    cnt = db.users.find().count()
    add_user()
    assert db.users.find().count() == cnt + len(test_names)


def test_del_user():
    del_user()
    add_user()
    cnt = db.users.find().count()
    del_user()
    assert db.users.find().count() == cnt - len(test_names)


def test_insert_matches():
    del_test_matches()
    cnt = db.match.find().count()
    insert_test_matches()
    assert db.match.find().count() == cnt + len(test_matches)
    insert_test_matches()
    assert db.match.find().count() == cnt + len(test_matches)
    del_test_matches()
    assert db.match.find().count() == cnt


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
            assert name in db.match.find_one({'id': a_id})[team]['player']
            assert name not in db.match.find_one({'id': a_id})[op[team]]['player']
    del_test_matches()


def test_result_correctness():
    del_test_matches()
    insert_test_matches()
    del_user()
    add_user()
    users_choose_teams()
    gamblers_series = model.generate_series(test_cup)
    cnt = 0
    for gambler, seris in gamblers_series.items():
        if gambler not in test_result:
            continue
        cnt += 1
        assert seris.latest_score == test_result[gambler]
    assert cnt == len(test_result)
    del_user()
    del_test_matches()

