import argparse
from worldcup.model import insert_auction
from worldcup.config import TOURNAMENTS
from worldcup.app import get_tournamentdb
from flask import Flask
from sys import argv

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("db", help="db name")
    parser.add_argument("gambler", help="gambler name")
    parser.add_argument("team", help="team name")
    parser.add_argument("price", help="bid price")
    args = parser.parse_args()

    dbname = argv[1]
    app = Flask('add_auction_%s' % (dbname))
    tournament = next((t for t in TOURNAMENTS if t.dbname == dbname), None)
    with app.app_context():
        get_tournamentdb(tournament)
    insert_auction(args.team, args.gambler, args.price)
    print('Done.')

