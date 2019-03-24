import bson.json_util
import click
from flask import g

from worldcup import model
from worldcup.app import app, dbclient, get_tournament
from worldcup.match_getter import populate_and_update


@app.cli.command('add_auction')
@click.argument('db')
@click.argument('team')
@click.argument('gambler', type=model.Gambler)
@click.argument('price', type=int)
def add_auction(db, gambler, team, price):
    g.tournament = get_tournament(db)
    auction = model.insert_auction(team=team, gambler=gambler, price=price)
    print(f'✅ add_auction: {auction}')


@app.cli.command('fetch_match')
@click.argument('db')
@click.option('--days', default=1, type=int, help='Fetch incoming matches in days.')
def fetch_match(db, days):
    g.tournament = get_tournament(db)
    populate_and_update(g.tournament.league, k=days)


@app.cli.command('import_collection')
@click.argument('db')
@click.argument('collection')
@click.argument('json', type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option('--drop', default=True, type=bool, help='Drop existing collection before import.')
def import_collection(db, collection, json, drop):
    with open(json) as f:
        data = [bson.json_util.loads(l) for l in f]
    ctl = dbclient[db][collection]
    if drop:
        ctl.drop()
    ctl.insert_many(data)
    print(f'✅ import_collection: {ctl.full_name} ({ctl.find().count()} records)')
