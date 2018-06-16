import datetime
import json
import os
import pytest

from collections import OrderedDict
from freezegun import freeze_time

from worldcup.app import db
from worldcup import model


def drop_all():
    db.gambler.drop()
    db.match.drop()
    db.auction.drop()


@pytest.fixture(autouse=True)
def setupforall():
    drop_all()
    yield
    drop_all()


@pytest.fixture
def g1():
    return model.insert_gambler('g1', 'openid-g1')


@pytest.fixture
def g2():
    return model.insert_gambler('g2', 'openid-g2')


@pytest.fixture
def g3():
    return model.insert_gambler('g3', 'openid-g3')


@pytest.fixture
def g4():
    return model.insert_gambler('g4', 'openid-g4')


@pytest.fixture
def match1():
    # simple handicap
    return model.insert_match('硬糙', datetime.datetime(2018, 3, 31, 19, 30), '受一球', '水宫', '利浦', 2.08, 1.78, 2, 4)


@pytest.fixture
def match2():
    # complex handicap
    return model.insert_match('硬糙', datetime.datetime(2018, 3, 31, 22, 10), '半球/一球', '纽尔联', '哈尔德', 2.02, 1.84, 2, 1)


@pytest.fixture
def auction2():
    test_auctions = [
        ('硬糙', '水宫', 'g4', 12),
        ('硬糙', '利浦', 'g3', 21),
        ('硬糙', '白顿', 'g2', 32),
        ('硬糙', '莱特城', 'g1', 1),
        ('硬糙', '曼特联', 'g2', 3),
        ('硬糙', '斯西', 'g3', 4),
        ('硬糙', '纽尔联', 'g4', 6),
        ('硬糙', '哈尔德', 'g1', 123),
    ]
    for auc in test_auctions:
        model.insert_auction(*auc)


##########
# insert_* tests
##########


def test_model_insert_match():
    model.insert_match('硬糙', datetime.datetime(2018, 3, 31, 19, 30), '受一球', '水宫', '利浦', 2.08, 1.78, 2, 4)
    assert db.match.find().count() == 1


def test_model_insert_auction():
    model.insert_auction('硬糙', '水宫', 'g0', 10)
    assert db.auction.find().count() == 1


##########
# find_* tests
##########


def test_find_one_gambler(g1):
    found = model.find_gambler_by_openid(g1.openid)
    assert found is not None and found.name == g1.name and found.openid == g1.openid
    assert model.find_gambler_by_openid('non-existent') is None

    found = model.find_gambler_by_name(g1.name)
    assert found is not None and found.name == g1.name and found.openid == g1.openid
    assert model.find_gambler_by_name('non-existent') is None


def test_model_find_gamblers(g1, g2, g3, g4):
    gamblers_found = model.find_gamblers()
    assert gamblers_found == [g1, g2, g3, g4]


def test_model_find_auction(auction2):
    auction_found = model.find_auction('硬糙', '纽尔联')
    assert auction_found is not None and auction_found.cup == '硬糙' and auction_found.team == '纽尔联'


def test_model_find_team_owner(auction2):
    team_owner = model.find_team_owner('硬糙', '纽尔联')
    assert team_owner == 'g4'


##########
# update_* test
##########


def test_model_update_match_score(match1):
    model.update_match_score(match1.id, "1", "0")
    match_found = model.find_match_by_id(match1.id)
    assert match_found.a['score'] == 1 and match_found.b['score'] == 0

    model.update_match_score(match1.id, "2", "3")
    match_found = model.find_match_by_id(match1.id)
    assert match_found.a['score'] == 2 and match_found.b['score'] == 3


def test_model_update_match_handicap(match1):
    # freeze_time() 须为 utc 时间

    with freeze_time('2018-03-31 04:00:01'):
        model.update_match_handicap(match1.id, '半球/一球')
        match_found = model.find_match_by_id(match1.id)
        assert match_found.handicap_display == '受一球' and match_found.handicap == (-1, -1)

    with freeze_time('2018-03-31 03:59:59'):
        model.update_match_handicap(match1.id, '半球/一球', cutoff_check=False)
        match_found = model.find_match_by_id(match1.id)
        assert match_found.handicap_display == '半球/一球' and match_found.handicap == (0.5, 1)


def test_model_update_match_gamblers(match1):
    # freeze_time() 须为 utc 时间

    # 盘口未定
    with freeze_time('2018-03-31 03:59:59'):
        model.update_match_gamblers(match1.id, 'a', 'g1')
        match_found = model.find_match_by_id(match1.id)
        assert 'g1' not in match_found.a['gamblers'] and 'g1' not in match_found.b['gamblers']

    # 盘口已定 开赛前 第一次投注
    with freeze_time('2018-03-31 04:00:01'):
        model.update_match_gamblers(match1.id, 'a', 'g1')
        match_found = model.find_match_by_id(match1.id)
        assert 'g1' in match_found.a['gamblers'] and 'g1' not in match_found.b['gamblers']

    # 盘口已定 开赛前 改注
    with freeze_time('2018-03-31 04:00:03'):
        model.update_match_gamblers(match1.id, 'b', 'g1')
        match_found = model.find_match_by_id(match1.id)
        assert 'g1' not in match_found.a['gamblers'] and 'g1' in match_found.b['gamblers']

    # 开赛后
    with freeze_time('2018-03-31 11:30:01'):
        model.update_match_gamblers(match1.id, 'a', 'g1')
        match_found = model.find_match_by_id(match1.id)
        assert 'g1' not in match_found.a['gamblers'] and 'g1' in match_found.b['gamblers']


def test_model_update_match_weight(match1):
    model.update_match_weight(match1.id, 4)
    match_found = model.find_match_by_id(match1.id)
    assert match_found.weight == 4


def test_model_update_match_time(match1):
    orig_time = match1.match_time

    next_time = orig_time + datetime.timedelta(hours=1)
    next_id = model._generate_match_id(match_time=next_time, team_a=match1.a['team'], team_b=match1.b['team'])

    assert model.find_match_by_id(match_id=next_id) is None

    model.update_match_time(match_id=match1.id, match_time=next_time)

    assert model.find_match_by_id(match_id=next_id).match_time == next_time


##########
# calculation tests
##########


@pytest.mark.parametrize('choice_a,choice_b,no_choice,handicap,score_a,score_b,expected', [
    (['g1', 'g2'], ['g3', 'g4'],      [],       '球半', '3', '1', {'g1': 2, 'g2': 2, 'g3': -2, 'g4': -2}),  # 有胜负
    (['g1', 'g2'], ['g3', 'g4'],      [],       '平手', '0', '0', {'g1': 0,  'g2': 0,  'g3': 0, 'g4': 0}),  # 平局
    (['g1', 'g2'], ['g3', 'g4'],      [], '受半球/一球', '1', '2', {'g1': -1, 'g2': -1, 'g3': 1, 'g4': 1}),  # 赢一半
    (['g1', 'g2'],       ['g3'],  ['g4'],       '半球', '0', '0', {'g1': -2, 'g2': -2, 'g3': 6, 'g4': -2}),  # 未投注
    (['g1', 'g2', 'g3', 'g4'],  [],   [], '受一球/球半', '0', '0', {'g1': 0, 'g2': 0, 'g3': 0, 'g4': 0}),  # 全胜
    (['g1', 'g2', 'g3', 'g4'],  [],   [], '一球/球半', '0', '0',   {'g1': -2, 'g2': -2, 'g3': -2, 'g4': -2}),  # 全负
])
def test_Match_update_profit_and_loss_no_auction(choice_a, choice_b, no_choice, handicap, score_a, score_b, expected):
    # prepare gamblers
    for g in choice_a + choice_b + no_choice:
        model.insert_gambler(name=g, openid=g)

    # prepare match
    match = model.insert_match('硬糙', datetime.datetime(2018, 3, 31, 19, 30), '受一球', '水宫', '利浦', 2.08, 1.78, 2, 4)

    # prepare bet choice
    for g in choice_a:
        model.update_match_gamblers(match.id, 'a', g, cutoff_check=False)

    for g in choice_b:
        model.update_match_gamblers(match.id, 'b', g, cutoff_check=False)

    # prepare match score
    model.update_match_score(match.id, score_a, score_b)

    # prepare match handicap
    model.update_match_handicap(match.id, handicap, cutoff_check=False)

    # calculate PNL
    match = model.find_match_by_id(match.id)
    result = match.update_profit_and_loss_result(required_gamblers=model.find_gamblers())

    for k, v in expected.items():
        assert result.get(k) == v


@pytest.mark.parametrize('choice_a,choice_b,no_choice,handicap,score_a,score_b,expected', [
    (['g1', 'g2'], ['g3', 'g4'],      [],       '球半', '3', '1', {'g1': 2, 'g2': 2, 'g3': -2, 'g4': -2}),  # 有胜负
    (['g1', 'g2'], ['g3', 'g4'],      [],       '平手', '0', '0', {'g1': 0,  'g2': 0,  'g3': 0, 'g4': 0}),  # 平局
    (['g1', 'g2'], ['g3', 'g4'],      [], '受半球/一球', '1', '2', {'g1': -1, 'g2': -1, 'g3': 2, 'g4': 2}),  # 赢一半
    (['g1', 'g2'],       ['g3'],  ['g4'],       '半球', '0', '0', {'g1': -2, 'g2': -2, 'g3': 12, 'g4': -2}),  # 未投注
    (['g1', 'g2', 'g3', 'g4'],  [],   [], '受一球/球半', '0', '0', {'g1': 0, 'g2': 0, 'g3': 0, 'g4': 0}),  # 全胜
    (['g1', 'g2', 'g3', 'g4'],  [],   [], '一球/球半', '0', '0',   {'g1': -2, 'g2': -2, 'g3': -2, 'g4': -2}),  # 全负
])
def test_Match_update_profit_and_loss_with_auction(choice_a, choice_b, no_choice, handicap, score_a, score_b, expected, auction2):
    # prepare gamblers
    for g in choice_a + choice_b + no_choice:
        model.insert_gambler(name=g, openid=g)

    # prepare match
    match = model.insert_match('硬糙', datetime.datetime(2018, 3, 31, 19, 30), '受一球', '水宫', '利浦', 2.08, 1.78, 2, 4)

    # prepare bet choice
    for g in choice_a:
        model.update_match_gamblers(match.id, 'a', g, cutoff_check=False)

    for g in choice_b:
        model.update_match_gamblers(match.id, 'b', g, cutoff_check=False)

    # prepare match score
    model.update_match_score(match.id, score_a, score_b)

    # prepare match handicap
    model.update_match_handicap(match.id, handicap, cutoff_check=False)

    # calculate PNL
    match = model.find_match_by_id(match.id)
    result = match.update_profit_and_loss_result(required_gamblers=model.find_gamblers())

    for k, v in expected.items():
        assert result.get(k) == v


def test_model_generate_series(g1, g2, g3, g4, match1, match2):
    results = model.generate_series('硬糙')
    json_results = [series.__dict__ for series in results]
    expected = [
        {'cup': '硬糙', 'gambler': 'g1', 'points': OrderedDict([('201803311930-水宫-利浦', -2.0), ('201803312210-纽尔联-哈尔德', -4.0)])},
        {'cup': '硬糙', 'gambler': 'g2', 'points': OrderedDict([('201803311930-水宫-利浦', -2.0), ('201803312210-纽尔联-哈尔德', -4.0)])},
        {'cup': '硬糙', 'gambler': 'g3', 'points': OrderedDict([('201803311930-水宫-利浦', -2.0), ('201803312210-纽尔联-哈尔德', -4.0)])},
        {'cup': '硬糙', 'gambler': 'g4', 'points': OrderedDict([('201803311930-水宫-利浦', -2.0), ('201803312210-纽尔联-哈尔德', -4.0)])}
    ]
    assert json_results == expected


##########
# integration tests
##########


def load_data(cup, filename):
    file_path = os.path.join(os.path.dirname(__file__), 'test_data', cup, filename)
    with open(file_path) as f:
        return json.load(f)


@pytest.fixture
def load_ecup():
    team = load_data('E_Cup', 'team.json')
    for t, g in team.items():
        model.insert_auction('E_cup', t, g, 1)

    players = load_data('E_Cup', 'players.json')
    for g, tmp in players.items():
        model.insert_gambler(g, g)

    for match_file in os.listdir(os.path.join(os.path.dirname(__file__), 'test_data', 'E_cup', 'match_data')):
        match_data = load_data('E_cup/match_data', match_file)
        match_date = datetime.datetime.strptime(str(match_data['date']), '%Y%m%d%H')
        match_obj = model.insert_match('E_Cup', match_date, '平手', match_data['teamA'],
                                       match_data['teamB'], 1, 1, match_data['scoreA'], match_data['scoreB'])
        db.match.update(
            {"id": match_obj.id},
            {"$set": {"handicap": (match_data['HandicapA'], match_data['HandicapB'])}, "$set": {
                "id": match_date.strftime("%Y%m%d") + match_data['teamA'] + match_data['teamB']}}

        )

    for bet_file in os.listdir(os.path.join(os.path.dirname(__file__), 'test_data', 'E_cup', 'bet_data')):
        bet_data = load_data('E_cup/bet_data', bet_file)
        match_obj = model.find_match_by_id(bet_data['ID'])
        for g, b in bet_data.items():
            if g != 'ID':
                if b == match_obj.a['team']:
                    model.update_match_gamblers(match_obj.id, g, 'a', cutoff_check=False)
                else:
                    model.update_match_gamblers(match_obj.id, g, 'b', cutoff_check=False)


# def test_load_ecup(load_ecup):
#     assert db.gambler.find().count() == 8
#     assert len(model.find_matches('E_Cup')) == 51
#     assert db.auction.find().count() == 24
