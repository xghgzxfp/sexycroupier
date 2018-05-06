# -*- coding: utf-8 -*-

import requests
import logging
import pytz
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from worldcup.model import insert_match, update_match_score, update_match_handicap

tz = pytz.timezone('Asia/Shanghai')

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
    return {st, ed}


def get_match_page(league, date, url='http://odds.sports.sina.com.cn/odds/index.php'):
    form_data = {
        'date': '',
        'type': '1',
        'league': league.encode('GBK'),
        'year': date.year,
        'month': date.month,
        'day': date.day
    }

    retry = 5
    logging.info('Getting data from website')
    connected = False
    r = None

    while retry and (not connected):
        logging.debug('Retries left:' + str(retry))
        try:
            r = requests.get(url, form_data, timeout=1)
            connected = True
        except Exception:
            retry -= 1

    if retry <= 0:
        raise Exception("Request tried out")

    logging.info('Request finished')
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
        scores = scores.split('-')
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
    current_time = datetime.now(tz=tz).replace(tzinfo=None)

    log_file_name = current_time.strftime('/tmp/%y-%m-%d-MatchGetter.log')
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s %(message)s')

    matches = get_match_data(league, date)
    logging.info('Match Data Collected from website')

    for match in matches:
        insert_match(*match)
        cutofftime = cutofftime_handicap(match[1])
        # if current time is 12 PM Beijing Time, then update handicap
        if current_time < cutofftime:
            update_match_handicap(match[1], match[3], match[4], match[2])
        # if current score not equal to what we have in db, then update
        update_match_score(match[1], match[3], match[4], match[-2], match[-1])
    return


def populate_and_update(league, k, current_date=datetime.now(tz=tz)):
    """
    :param league: league filter
    :param current_date: the date from which getter starts
    :param k: get match data within k days
    :return:
    """
    for day_diff in range(0, k + 1):
        populate_match(league, current_date + timedelta(days=day_diff))
    return


if __name__ == "__main__":
    while(1):
        try:
            populate_and_update('阿甲', 0)
        except Exception as error:
            logging.info(error.args[0])
            continue
        time.sleep(20)