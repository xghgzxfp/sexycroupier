# -*- coding: utf-8 -*-

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from worldcup.model import insert_match, update_match_score


def get_match_page(league, date, url='http://odds.sports.sina.com.cn/odds/index.php'):
    form_data = {
        'date': '',
        'type': '1',
        'league': league.encode('GBK'),
        'year': date.year,
        'month': date.month,
        'day': date.day
    }
    r = requests.get(url, form_data)
    r.encoding = 'GBK'
    return r.text

'''
def convert_handicap(origin_handicap):
    handicaps = origin_handicap.split('/')
'''


def parse_teams(team_str):
    teams = team_str.findAll(text=True)
    if len(teams) == 4:
        return [teams[1][:-2], teams[3]]
    else:
        teams = teams[0].split('vs')
        return [teams[0], teams[1]]


def parse_scores(score_str):
    scores = score_str.find(text=True)
    if '-' not in scores:
        return ['', '']
    else:
        scores = score_str.split('-')
        return [scores[0], scores[1]]


def get_match_data(league, date):
    result = list()

    page = get_match_page(league, date)
    soup = BeautifulSoup(page, "html5lib")
    table = soup.find("table", {"class": "TableStyle"})

    # ignore hidden rows
    tbodies = table.findAll("tbody", {"id": None})
    for tbody in tbodies:
        for row in tbody.findAll("tr"):
            cells = row.findAll("td")
            if not cells or cells[0].find(text=True) == '暂无数据':
                continue
            league_name = cells[0].find(text=True)
            match_time_hhmm = cells[1].find(text=True)
            teams = parse_teams(cells[2])
            team_a = teams[0]
            team_b = teams[1]
            premium_a = cells[3].find(text=True).replace(u'\xa0', u'')
            handicap_display = cells[4].find(text=True).replace(u'\xa0', u'')
            premium_b = cells[5].find(text=True).replace(u'\xa0', u'')
            match_time = datetime.strptime(date.strftime("%Y%m%d") + " " + match_time_hhmm, "%Y%m%d %H:%M")
            scores = parse_scores(cells[15])
            score_a = scores[0]
            score_b = scores[1]
            match_entry = [league_name, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b]
            result.append(match_entry)
    return result


def populate_match(league, date):
    for match in get_match_data(league, date):
        insert_match(*match)
    return

def update_match_scores(league, date):
    for match in get_match_data(league, date):
        update_match_score(match[1], match[3], match[4], match[7], match[8])
    return

def populate_and_update(league, current_date=datetime.now()):
    populate_match(league, current_date)
    populate_match(league, current_date + timedelta(days=1))
    populate_match(league, current_date + timedelta(days=2))
    populate_match(league, current_date + timedelta(days=3))
    populate_match(league, current_date + timedelta(days=4))
    populate_match(league, current_date + timedelta(days=5))
    populate_match(league, current_date + timedelta(days=6))
    populate_match(league, current_date + timedelta(days=7))
    update_match_scores(league, current_date)
    return


if __name__ == "__main__":
    """
    print match data that
    Match Date, Team A, Team B, Premium A, Handicap, Premium B, ...
    """
    populate_and_update('意甲')