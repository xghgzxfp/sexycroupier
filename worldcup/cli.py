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


@app.cli.command('update_weight')
@click.argument('db')
@click.argument('match_id')
@click.argument('new_weight', type=int)
def update_weight(db, match_id, new_weight):
    g.tournament = get_tournament(db)
    match = model.update_match_weight(match_id=match_id, weight=new_weight)
    print(f'✅ update_weight: {match_id} now with weight as {new_weight}')


@app.cli.command('fetch_match')
@click.argument('db')
def fetch_match(db):
    g.tournament = get_tournament(db)
    populate_and_update(g.tournament.league, g.tournament.weight_schedule)


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
