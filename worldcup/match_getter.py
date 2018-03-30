# -*- coding: utf-8 -*-

import requests
from datetime import datetime
from bs4 import BeautifulSoup


def get_match_page(league, year, month, day, url='http://odds.sports.sina.com.cn/odds/index.php'):
    form_data = {
        'date': '',
        'type': '1',
        'league': league.encode('GBK'),
        'year': year,
        'month': month,
        'day': day
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


def parse_match_data(league, year, month, day):
    result = list()

    page = get_match_page(league, year, month, day)
    soup = BeautifulSoup(page, "html5lib")
    table = soup.find("table", {"class": "TableStyle"})
    tbodies = table.findAll("tbody", {"id": None})

    for tbody in tbodies:
        for row in tbody.findAll("tr"):
            cells = row.findAll("td")
            if not cells:
                continue
            league_name = cells[0].find(text=True)
            match_time_hhmm = cells[1].find(text=True)
            teams = parse_teams(cells[2])
            team_a = teams[0]
            team_b = teams[1]
            premium_a = cells[3].find(text=True).replace(u'\xa0', u'')
            handicap = cells[4].find(text=True).replace(u'\xa0', u'')
            premium_b = cells[5].find(text=True).replace(u'\xa0', u'')
            match_time = datetime.strptime(year + month + day + " " + match_time_hhmm, "%Y%m%d %H:%M")

            scores = parse_scores(cells[15])
            score_a = scores[0]
            score_b = scores[1]
            match_entry = [league_name, match_time, team_a, team_b, handicap, premium_a, premium_b, score_a, score_b]
            result.append(match_entry)
    return result


if __name__ == "__main__":
    """
    print match data that
    Match Date, Team A, Team B, Premium A, Handicap, Premium B, ...
    """
    for match in parse_match_data('', '2018', '03', '31'):
        print(match)
