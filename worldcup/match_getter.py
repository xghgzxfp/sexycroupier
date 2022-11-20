import datetime
import logging
import requests
import html

from worldcup import config, constant
from worldcup.model import insert_match, update_match_score, update_match_handicap, utc_to_beijing


def get_json_data_from_url(url, method):
    logging.info(f"Requesting data: {url} ")

    retry = 10
    while retry:
        try:
            if method == "get":
                r = requests.get(url, timeout=1)
            else:
                r = requests.post(url, timeout=5)
            break
        except Exception:
            retry -= 1

    if retry <= 0:
        raise Exception("Request failed")

    r.encoding = "UTF-8"
    logging.info("Request finished: url={} status={}".format(r.url, r.status_code))
    return r.json().get("data")


def get_match_data(league):
    event_url = "https://www.macauslot.com/gate/gb/big5.macauslot.com/soccer/json/realtime/threeinone_event_sc_fb.json"
    odds_url = "https://www.macauslot.com/gate/gb/big5.macauslot.com/soccer/json/realtime/threeinone_odds_sc_fb.json"
    score_url = "https://www.macauslot.com/infoApi/sc/D/FB/matchs/livescore"

    # initialize event_id to match_entry
    event_id_to_match_entry = {}
    for event_detail in get_json_data_from_url(event_url, "get"):
        if event_detail.get("event_type_en") == league:
            match_entry = {
                "league_name": event_detail["event_type_en"],
                "team_a": html.unescape(event_detail["event"]["home_team"]),
                "team_b": html.unescape(event_detail["event"]["away_team"]),
                "match_time": datetime.datetime.strptime(event_detail["event"]["start_time"], "%Y-%m-%d %H:%M:%S"),
            }
            match_entry["match_time_hhmm"] = match_entry["match_time"].strftime("%H:%M")

            event_id_to_match_entry[
                event_detail.get("event").get("ev_id")
            ] = match_entry

    # merge handicap and premium into match entry map
    for odd_detail in get_json_data_from_url(odds_url, "get"):
        if odd_detail.get("ev_id") in event_id_to_match_entry.keys():
            market = odd_detail.get("markets")[len(odd_detail.get("markets")) > 1]
            event_id_to_match_entry[odd_detail.get("ev_id")]["premium_a"] = market.get(
                "outcomes"
            )[0].get("rate")
            event_id_to_match_entry[odd_detail.get("ev_id")]["premium_b"] = market.get(
                "outcomes"
            )[1].get("rate")
            event_id_to_match_entry[odd_detail.get("ev_id")][
                "handicap_display"
            ] = get_handicap_display(market.get("hcap_disp"))

    # populate scores
    for score_detail in get_json_data_from_url(score_url, "post").get("list"):
        if score_detail.get("ev_id") in event_id_to_match_entry.keys():
            if score_detail.get("score") == None:
                event_id_to_match_entry.get(score_detail.get("ev_id"))["score_a"] = "0"
                event_id_to_match_entry.get(score_detail.get("ev_id"))["score_b"] = "0"
            else:
                scores = parse_scores(score_detail.get("score").get("current"))
                event_id_to_match_entry.get(score_detail.get("ev_id"))[
                    "score_a"
                ] = scores[0]
                event_id_to_match_entry.get(score_detail.get("ev_id"))[
                    "score_b"
                ] = scores[1]

    result = []

    for match_entry in event_id_to_match_entry.values():
        match = [
            match_entry.get("league_name"),
            match_entry.get("match_time"),
            match_entry.get("handicap_display"),
            match_entry.get("team_a"),
            match_entry.get("team_b"),
            match_entry.get("premium_a"),
            match_entry.get("premium_b"),
            match_entry.get("score_a"),
            match_entry.get("score_b"),
        ]
        result.append(match)
    return result


def parse_scores(score_str):
    scores = score_str.find(text=True)
    if ":" not in scores:
        return ["", ""]
    else:
        scores = scores.split(":")
        return [scores[0], scores[1]]


def get_handicap_display(handicap_in_num):
    if "/" not in handicap_in_num:
        return map_handicap_in_num_to_display(handicap_in_num)
    else:
        handicap_in_nums = handicap_in_num.split("/")
        return "{}/{}".format(
            map_handicap_in_num_to_display(handicap_in_nums[0]),
            map_handicap_in_num_to_display(handicap_in_nums[1]),
        )


def map_handicap_in_num_to_display(handicap_in_num):
    if "+" in handicap_in_num:
        return f"受{constant.HANDICAP_DICT[handicap_in_num[1:]]}"
    if "-" in handicap_in_num:
        return constant.HANDICAP_DICT[handicap_in_num[1:]]
    else:
        return constant.HANDICAP_DICT[handicap_in_num]


def populate_match(league, weight_schedule, date):
    # utcnow = datetime.datetime.utcnow()
    # log_file_name = utcnow.strftime('/tmp/bet_web/%y-%m-%d-MatchGetter.log')
    # logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s %(message)s')
    matches = get_match_data(league)
    print(f'Matches collected: date="{date}" league={league} count={len(matches)}')

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
        print(
            league,
            match_time,
            handicap_display,
            team_a,
            team_b,
            score_a,
            score_b,
            weight,
        )
        match = insert_match(league, match_time, handicap_display, team_a, team_b, premium_a, premium_b, score_a, score_b, weight)
        update_match_handicap(match_id=match.id, handicap_display=handicap_display)
        update_match_score(match_id=match.id, score_a=score_a, score_b=score_b)
    return


def populate_and_update(league, weight_schedule, k=1, current_date=None):
    """Populate and update matches in the given league.

    :param league: league filter
    :param k: get match data within k days
    :param current_date: the date from which getter starts
    :return:
    """
    current_date = current_date or utc_to_beijing(datetime.datetime.utcnow())
    populate_match(league, weight_schedule, date=current_date + datetime.timedelta(days=k))
    return
