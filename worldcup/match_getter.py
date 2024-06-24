import time
import datetime
import logging
import requests

from worldcup import constant
from worldcup.model import insert_match, update_match_score, update_match_handicap, utc_to_beijing, find_match_by_id, _generate_match_id


UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'


def retry(func):
    # @functools.wraps
    def _(*args, **kwargs):
        retry = 10
        while retry:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(e)
                retry -= 1
        raise Exception("max retries")
    return _


def get_match_data(league, current_date):
    url_odds = f"https://www.macauslot.com/soccer/json/realtime/threeinone_odds_sc_fb.json?nocache={int(time.time() * 1000)}"
    url_event = "https://www.macauslot.com/infoApi/cn/D/FB/matchs/list"

    r = retry(requests.get)(url_odds, headers={"User-Agent": UA})
    odds = dict()
    for od in r.json()["data"]:
        market = [m for m in od["markets"] if m["name"] == "让球盘"][0]
        odds[od["ev_id"]] = market["hcap_disp"]

    events = []
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    # 昨天
    date = str((current_date - datetime.timedelta(days=1)).date())
    r = retry(session.post)(url_event, json=dict(date=date))
    try: events += r.json()["data"]["list"]
    except Exception: print(r.content, r.request.headers)

    # 今天
    date = str(current_date.date())
    r = retry(session.post)(url_event, json=dict(date=date))
    events += r.json()["data"]["list"]

    # from now
    r = retry(session.post)(url_event)
    events += r.json()["data"]["list"]

    seen = set()
    matches = []
    for ev in events:
        # 忽略非 league 场次
        if ev["uqTournament"]["nameZh"] != league:
            continue
        evid = ev["evId"]
        # 忽略已处理场次
        if evid in seen:
            print(f'skip seen: {evid}')
            continue
        seen.add(evid)
        # 构造 match
        match_time = datetime.datetime.strptime(ev["startDate"], "%Y-%m-%d %H:%M")
        team_a = ev["hometeamNameZh"]
        team_b = ev["awayteamNameZh"]
        handicap = ev.get("hcap", dict()).get("ftHandicap", "")
        handicap = handicap or odds.get(evid)
        # 无法取得 handicap 则跳过
        if not handicap:
            match = find_match_by_id(_generate_match_id(match_time, team_a, team_b))
            if not match:
                print(f'skip no handicap: {team_a} vs {team_b}')
                continue
            handicap_display = match.handicap_display
        else:
            handicap_display = _handicap_display(handicap)
        score = ev.get("score", dict()).get("ft")
        score_a, score_b = score.split(":") if score else (None, None)
        # 完成构造
        matches.append((
            league,
            match_time,
            handicap_display,
            team_a,
            team_b,
            0,  # premium_a
            0,  # premium_b
            score_a,
            score_b,
        ))

    return sorted(matches, key=lambda m: m[1])


def _handicap_display(handicap_in_num):
    handicaps = []
    for h in handicap_in_num.split("/"):
        if "+" in h:
            handicaps.append(f"受{constant.HANDICAP_DICT[h[1:]]}")
            continue
        handicaps.append(constant.HANDICAP_DICT[h[1:]] if "-" in h else constant.HANDICAP_DICT[h])
    return "/".join(handicaps)


def populate_and_update(league, weight_schedule, k=1, current_date=None, dry_run=False):
    """Populate and update matches in the given league.

    :param league: league filter
    :param k: get match data within k days
    :param current_date: the date from which getter starts
    :return:
    """
    current_date = current_date or utc_to_beijing(datetime.datetime.utcnow())
    date = current_date + datetime.timedelta(days=k)

    # utcnow = datetime.datetime.utcnow()
    # log_file_name = utcnow.strftime('/tmp/bet_web/%y-%m-%d-MatchGetter.log')
    # logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s %(message)s')
    matches = get_match_data(league, current_date=current_date)
    print(f'matches fetched: date="{date}" league={league} count={len(matches)} dry_run={dry_run}')

    for (
        league,
        match_time,
        handicap_display,
        team_a,
        team_b,
        premium_a,
        premium_b,
        score_a,
        score_b,
    ) in matches:
        # 跳过尚早比赛
        if match_time > date:
            continue
        # 根据 weight schedule 取得对应权重
        weight = 2
        for (t, w) in weight_schedule:
            if match_time < t:
                weight = w
                break
        print(league, match_time, handicap_display, team_a, team_b, score_a, score_b, weight)
        if dry_run: continue
        match = insert_match(
            league=league,
            match_time=match_time,
            handicap_display=handicap_display,
            team_a=team_a,
            team_b=team_b,
            premium_a=premium_a,
            premium_b=premium_b,
            score_a=score_a,
            score_b=score_b,
            weight=weight,
        )
        update_match_handicap(match_id=match.id, handicap_display=handicap_display)
        update_match_score(match_id=match.id, score_a=score_a, score_b=score_b)
