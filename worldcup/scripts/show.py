import argparse
from pprint import pprint
from worldcup.app  import db

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--gambler", help="show all gambler data in db", action="store_true")
    parser.add_argument("-m", "--match", help="show all match data in db", action="store_true")
    parser.add_argument("-n", "--auction", help="show all auction data in db", action="store_true")
    parser.add_argument("-a", "--all", help="show ALL data in db", action="store_true")
    args = parser.parse_args()

    cols = []
    if args.gambler:
        cols.append(db.gambler)
    if args.match:
        cols.append(db.match)
    if args.auction:
        cols.append(db.auction)
    if args.all:
        cols = [db.gambler, db.match, db.auction]

    for col in cols:
        print(col)
        pprint(list(col.find()))


