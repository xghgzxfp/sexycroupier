import argparse
from worldcup.model import insert_auction

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("gambler", help="gambler name")
    parser.add_argument("team", help="team name")
    parser.add_argument("price", help="bid price")
    args = parser.parse_args()

    insert_auction(args.team, args.gambler, args.price)
    print('Done.')

