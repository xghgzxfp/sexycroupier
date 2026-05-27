import time
import datetime
import logging
import requests

import re
import base64
import codecs
from requests import Response, PreparedRequest
from requests.adapters import HTTPAdapter

from worldcup import constant
from worldcup.model import insert_match, update_match_score, update_match_handicap, utc_to_beijing, find_match_by_id, _generate_match_id


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Origin": "https://www.macauslot.com",
    "Referer": "https://www.macauslot.com/cn/soccer/fixture.html",
}


class AcwScV2Adapter(HTTPAdapter):
    COOKIE_KEY = "acw_sc__v2"
    COOKIE_VALUE = None

    def _parse_js_string(self, s: str) -> bytes:
        return codecs.escape_decode(s.strip("'\"").encode("utf-8"))[0]

    def _rc4_str(self, data: str, key: str) -> str:
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]

        i = j = 0
        output = []
        for char in data:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            output.append(chr(ord(char) ^ s[(s[i] + s[j]) % 256]))
        return "".join(output)

    def _unbox(self, s: str, shuffles: list) -> str:
        return "".join(s[v - 1] for v in shuffles if v - 1 < len(s))

    def _hexor(self, hex1: str, hex2: str) -> str:
        return bytes(a ^ b for a, b in zip(bytes.fromhex(hex1), bytes.fromhex(hex2))).hex()

    def _solve(self, html_content: str) -> str:
        code = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html_content, re.DOTALL))

        arg1_match = re.search(r'var\s+arg1\s*=\s*[\'"]([^\'"]+)[\'"]', code)
        if not arg1_match:
            raise ValueError("arg1 not found")
        arg1 = arg1_match.group(1)

        iife_match = re.search(
            r"\}\s*\(\s*([a-zA-Z0-9_$]+)\s*,\s*(0x[0-9a-fA-F]+|[0-9]+)\s*\)\s*\)\s*;",
            code,
        )
        if not iife_match:
            raise ValueError("iife array shift match not found")
        array_name = iife_match.group(1)
        num_shifts = int(iife_match.group(2), 0)

        array_pattern = r"var\s+" + re.escape(array_name) + r"\s*=\s*\[(.*?)\]\s*;"
        array_match = re.search(array_pattern, code)
        if not array_match:
            raise ValueError(f"Array {array_name} not found")

        ciphers = [self._parse_js_string(el) for el in re.findall(r"'[^']*'|\"[^\"]*\"", array_match.group(1))]

        if num_shifts:
            num_shifts %= len(ciphers)
            ciphers = ciphers[num_shifts:] + ciphers[:num_shifts]

        func_match = re.search(
            r"var\s+([a-zA-Z0-9_$]+)\s*=\s*function\s*\(\s*([a-zA-Z0-9_$]+)\s*,\s*[a-zA-Z0-9_$]+\s*\)\s*\{\s*var\s+\2\s*=\s*parseInt\s*\(\s*\2\s*,\s*(0x10|16)\s*\)\s*;",
            code,
        )
        if not func_match:
            raise ValueError("decryption function match not found")
        func_name = func_match.group(1)

        keys = {}
        key_pattern = re.escape(func_name) + r'\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)'
        for match in re.finditer(key_pattern, code):
            keys[int(match.group(1), 0)] = self._parse_js_string(match.group(2))

        decrypted_key = self._rc4_str(
            base64.b64decode(ciphers[3]).decode("utf-8"),
            keys[3].decode("utf-8"),
        )

        shuffles_match = re.search(
            r"\[\s*(?:(?:0x[0-9a-fA-F]+|[0-9]+)\s*,\s*){39}(?:0x[0-9a-fA-F]+|[0-9]+)\s*\]",
            code,
        )
        if not shuffles_match:
            raise ValueError("shuffles array not found")
        shuffles = [int(x.strip(), 0) for x in shuffles_match.group(0).strip("[]").split(",")]

        return self._hexor(decrypted_key, self._unbox(arg1, shuffles))

    def _update_cookie_header(self, request: PreparedRequest, value: str) -> None:
        cookie_header = request.headers.get("Cookie", "")
        if f"{self.COOKIE_KEY}=" in cookie_header:
            cookie_header = re.sub(
                rf"{self.COOKIE_KEY}=[^;]*",
                f"{self.COOKIE_KEY}={value}",
                cookie_header,
            )
        else:
            cookie_header = "; ".join(p for p in [cookie_header, f"{self.COOKIE_KEY}={value}"] if p)
        request.headers["Cookie"] = cookie_header

    def send(self, request: PreparedRequest, **kwargs) -> Response:
        if AcwScV2Adapter.COOKIE_VALUE is not None:
            self._update_cookie_header(request, AcwScV2Adapter.COOKIE_VALUE)

        response = super(AcwScV2Adapter, self).send(request, **kwargs)
        if "var arg1=" in response.text and self.COOKIE_KEY in response.text:
            AcwScV2Adapter.COOKIE_VALUE = self._solve(response.text)
            self._update_cookie_header(request, AcwScV2Adapter.COOKIE_VALUE)
            return super(AcwScV2Adapter, self).send(request, **kwargs)
        return response


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

    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", AcwScV2Adapter())

    r = retry(session.get)(url_odds)
    odds = dict()
    for od in r.json()["data"]:
        market = [m for m in od["markets"] if m["name"] == "让球盘"][0]
        odds[od["ev_id"]] = market["hcap_disp"]

    events = []

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
