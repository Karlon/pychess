import os
import sys
from datetime import date

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

#from profilehooks import profile

from sqlalchemy import *

from pychess.Utils.const import *
from pychess.Savers.pgn import load
from pychess.System.prefix import addDataPrefix


CHUNK = 1000

metadata = MetaData()

names_table = Table('names', metadata,
    Column('id', Integer, Sequence('names_id_seq'), primary_key=True),
    Column('name', String)
    )

games_table = Table('games', metadata,
    Column('id', Integer, Sequence('games_id_seq'), primary_key=True),
    Column('event', Integer, ForeignKey('names.id')),
    Column('site', Integer, ForeignKey('names.id')),
    Column('date_year', SmallInteger),
    Column('date_month', SmallInteger),
    Column('date_day', SmallInteger),
    Column('round', SmallInteger),
    Column('white', Integer, ForeignKey('names.id')),
    Column('black', Integer, ForeignKey('names.id')),
    Column('result', SmallInteger),
    Column('white_elo', SmallInteger),
    Column('black_elo', SmallInteger),
    Column('white_title', String(3)),
    Column('black_title', String(3)),
    Column('ply_count', SmallInteger),
    Column('eco', CHAR(3)),
    Column('board', SmallInteger),
    Column('fen', String(88)),
    Column('annotator', Integer, ForeignKey('names.id')),
    Column('source', Integer, ForeignKey('names.id')),
    Column('movetext', String)
    )

#@profile
def import_from_pgn(file, conn, maxid):
    cf = load(open(file))

    ins_names = names_table.insert()
    ins_games = games_table.insert()

    # initialise names dict to speed up lookup of names
    s = select([names_table])
    names = dict([(n.name, n.id) for n in conn.execute(s)])

    # collect new names not in names dict yet, and commit them only at end
    name_data = []
    def get_id(name):
        if not name:
            return None

        if name in names:
            return names[name]
        else:
            global maxid
            name_data.append({'name':name})
            maxid += 1
            names[name] = maxid
            return maxid

    # use transaction to avoid autocommit slowness
    trans = conn.begin()
    try:
        # collect new games and commit them in big chunks for speed
        game_data = []
        for i, game in enumerate(cf.games):
            event = get_id(cf._getTag(i, 'Event'))
            site = get_id(cf._getTag(i, 'Site'))
            game_date = cf._getTag(i, 'Date')
            if game_date and not '?' in game_date:
                game_year, game_month, game_day = map(int, game_date.split('.'))
            elif game_date and not '?' in game_date[:4]:
                game_year, game_month, game_day = int(game_date[:4]), None, None
            else:
                game_year, game_month, game_day = None, None, None
            round = cf._getTag(i, 'Round')
            try:
                round = int(round)
            except:
                round = None
            white, black = cf.get_player_names(i)
            white = get_id(white)
            black = get_id(black)
            result = cf.get_result(i)
            white_elo = cf._getTag(i, 'WhiteElo')
            black_elo = cf._getTag(i, 'BlackElo')

            ply_count = cf._getTag(i, "PlyCount")
            event_date = cf._getTag(i, 'EventDate')
            eco = cf._getTag(i, "ECO")
            if eco:
                eco = eco[:3]
            fen = cf._getTag(i, "FEN")
            annotator = get_id(cf._getTag(i, "Annotator"))
            source = get_id(cf._getTag(i, "Source"))
            movetext = game[1]
            
            if len(game_data) < CHUNK:
                game_data.append({
                    'event':event,
                    'site':site,
                    'date_year':game_year,
                    'date_month':game_month,
                    'date_day':game_day,
                    'round':round,
                    'white':white,
                    'black':black,
                    'result':result,
                    'white_elo':white_elo,
                    'black_elo':black_elo,
                    'ply_count':ply_count,
                    'eco':eco,
                    'fen':fen,
                    'annotator':annotator,
                    'source':source,
                    'movestr':movetext})
            else:
                if name_data:
                    conn.execute(ins_names, name_data)
                    print "added %s records to names table" % len(name_data)
                    name_data = []

                conn.execute(ins_games, game_data)
                print "added %s records to games table" % CHUNK
                game_data = []
            
        if name_data:
            conn.execute(ins_names, name_data)
            print "added %s records to names table" % len(name_data)
        if game_data:
            conn.execute(ins_games, game_data)
            print "added %s records to games table" % len(game_data)

        trans.commit()
    except:
        trans.rollback()
        raise


if __name__ == "__main__":
    # TODO: make the dbdriver configurable
    #path = "sqlite:///" + os.path.join(addDataPrefix("pychess.pdb"))
    path = "firebird://sysdba:masterkey@localhost//home/tamas/data/pychess.db"
    
    engine = create_engine(path, echo=False)
    conn = engine.connect()

    metadata.drop_all(engine)
    metadata.create_all(engine)

    # get the bigest names.id to use it for manual increment
    s = select([func.max(names_table.c.id).label('maxid')])
    maxid = conn.execute(s).scalar()
    if maxid is None:
        maxid = 0

    import_from_pgn(sys.argv[1], conn, maxid)

    # aliases used for different kind of names
    a1 = names_table.alias()
    a2 = names_table.alias()
    a3 = names_table.alias()
    a4 = names_table.alias()

    s = select([games_table.c.id, a1.c.name, a2.c.name, a3.c.name, a4.c.name,
                games_table.c.date_year, games_table.c.date_month,games_table.c.date_day,
                games_table.c.result, games_table.c.white_elo, games_table.c.black_elo],
                and_(
                games_table.c.event==a1.c.id,
                games_table.c.site==a2.c.id,
                games_table.c.white==a3.c.id,
                games_table.c.black==a4.c.id))
                 
    #for g in conn.execute(s):
        #print "%s %s %s %s %s %s %s %s %s %s %s" % (g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7], reprResult[g[8]], g[9], g[10])

    #s = select([names_table])
    #names = dict([(n.id, n.name) for n in conn.execute(s)])
    #print names

    sys.exit()