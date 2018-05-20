import argparse
from worldcup.app  import db

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--gambler", help="delete all gambler data in db", action="store_true")
    parser.add_argument("-m", "--match", help="delete all match data in db", action="store_true")
    parser.add_argument("-n", "--auction", help="delete all auction data in db", action="store_true")
    parser.add_argument("-a", "--all", help="delete ALL data in db", action="store_true")
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
        col.delete_many({})

    print('All data deleted. Now you can run away!')

