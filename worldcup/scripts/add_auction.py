import argparse
from worldcup.model import insert_auction
from pymongo import MongoClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("dbname", help="db name")
    parser.add_argument("gambler", help="gamber name")
    parser.add_argument("team", help="team name")
    parser.add_argument("price", help="auction price")
    args = parser.parse_args()

    db = MongoClient('mongodb://localhost:27017/')[args.dbname]
    insert_auction(args.team, args.gambler, args.price, db)
    print('Done.')

