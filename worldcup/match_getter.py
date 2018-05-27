# -*- coding: utf-8 -*-

import datetime
import logging
import requests

from bs4 import BeautifulSoup

from worldcup.model import insert_match, update_match_score, update_match_handicap, utc_to_beijing
from worldcup.app import config


def get_match_page(league, date, url='http://odds.sports.sina.com.cn/odds/index.php'):
    form_data = {
        'date': '',
        'type': '1',
        'league': league.encode('GBK'),
        'year': date.year,
        'month': date.month,
        'day': date.day
    }

    logging.info('Getting data from website: date="{}"'.format(date))

    retry = 5
    while retry:
        try:
            r = requests.get(url, form_data, timeout=1)
            break
        except Exception:
            retry -= 1

    if retry <= 0:
        raise Exception("Request failed")

    r.encoding = 'GBK'

    logging.info('Request finished: url={} status={}'.format(r.url, r.status_code))
    return r.text


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
            match_time = datetime.datetime.strptime(date.strftime("%Y%m%d") + " " + match_time_hhmm, "%Y%m%d %H:%M")
            scores = parse_scores(cells[15])
            score_a = scores[0]
            score_b = scores[1]
            match_entry = [league_name, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b]
            result.append(match_entry)
    return result


def populate_match(league, date):
    current_time = datetime.datetime.utcnow()
    log_file_name = current_time.strftime('/tmp/bet_web/%y-%m-%d-MatchGetter.log')
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s %(message)s')
    matches = get_match_data(league, date)
    logging.info('Matches collected: date="{}" cup={} count={}'.format(date, league, len(matches)))

    for match in matches:
        new_match = insert_match(*match)
        # if current time is 12 PM Beijing Time, then update handicap
        if utc_to_beijing(current_time) < new_match.handicap_cutoff_time:
            update_match_handicap(new_match.match_time, new_match.a['team'], new_match.b['team'], new_match.handicap_display)
        # if current score not equal to what we have in db, then update
        update_match_score(new_match.match_time, new_match.a['team'], new_match.b['team'], new_match.a['score'], new_match.b['score'])
    return


def populate_and_update(league, k=1, current_date=utc_to_beijing(datetime.datetime.utcnow())):
    """
    :param league: league filter
    :param current_date: the date from which getter starts
    :param k: get match data within k days
    :return:
    """
    for day_diff in range(0, k + 1):
        populate_match(league, current_date + datetime.timedelta(days=day_diff))
    return


if __name__ == "__main__":
    try:
        populate_and_update(config.LEAGUE_NAME)
    except Exception as error:
        logging.info(error.args[0])