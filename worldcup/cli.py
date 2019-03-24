import click
from flask import g

from worldcup import model
from worldcup.app import app, get_tournament
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
def fetch_match(db, k):
    g.tournament = get_tournament(db)
    populate_and_update(g.tournament.league, k=k)
