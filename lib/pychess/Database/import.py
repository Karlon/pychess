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
    Column('id', Integer, primary_key=True),
    Column('name', String)
    )

games_table = Table('games', metadata,
    Column('id', Integer, primary_key=True),
    Column('event', Integer, ForeignKey('names.id')),
    Column('site', Integer, ForeignKey('names.id')),
    Column('date', Date),
    Column('round', SmallInteger),
    Column('white', Integer, ForeignKey('names.id')),
    Column('black', Integer, ForeignKey('names.id')),
    Column('result', SmallInteger),
    Column('white_elo', SmallInteger),
    Column('black_elo', SmallInteger),
    Column('white_title', String(3)),
    Column('black_title', String(3)),
    Column('ply_count', SmallInteger),
    Column('event_date', Date),
    Column('eco', CHAR(3)),
    Column('board', SmallInteger),
    Column('fen', String(64)),
    Column('annotator', Integer, ForeignKey('names.id')),
    Column('source', Integer, ForeignKey('names.id')),
    Column('movetext', Text)
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
            event = get_id(cf.get_event(i))
            site = get_id(cf.get_site(i))
            y, m, d = cf.get_date(i)
            game_date = date(y, m, d)
            round = cf.get_round(i)
            white, black = cf.get_player_names(i)
            white = get_id(white)
            black = get_id(black)
            result = cf.get_result(i)
            white_elo, black_elo = cf.get_elo(i)

            ply_count = cf._getTag(i, "PlyCount")
            y, m, d = cf.get_event_date(i)
            event_date = date(y, m, d)
            eco = cf._getTag(i, "ECO")
            fen = cf._getTag(i, "FEN")
            annotator = get_id(cf._getTag(i, "Annotator"))
            source = get_id(cf._getTag(i, "Source"))
            movetext = game[1]
            
            if len(game_data) < CHUNK:
                game_data.append({
                    'event':event,
                    'site':site,
                    'date':game_date,
                    'round':round,
                    'white':white,
                    'black':black,
                    'result':result,
                    'white_elo':white_elo,
                    'black_elo':black_elo,
                    'ply_count':ply_count,
                    'event_date':event_date,
                    'eco':eco,
                    'fen':fen,
                    'annotator':annotator,
                    'source':source,
                    'movestr':movetext})
            else:
                conn.execute(ins_games, game_data)
                game_data = []
                print "added %s records to games table" % CHUNK
            
        if game_data:
            conn.execute(ins_games, game_data)
            print "added %s records to games table" % len(game_data)

        conn.execute(ins_names, name_data)
        print "added %s records to names table" % len(name_data)

        trans.commit()
    except:
        trans.rollback()
        raise


if __name__ == "__main__":
    # TODO: make the dbdriver configurable
    path = "sqlite:///" + os.path.join(addDataPrefix("pychess.pdb"))
    
    engine = create_engine(path, echo=False)
    conn = engine.connect()

#    metadata.drop_all(engine)
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
                games_table.c.date, games_table.c.result, games_table.c.white_elo, games_table.c.black_elo],
                and_(
                games_table.c.event==a1.c.id,
                games_table.c.site==a2.c.id,
                games_table.c.white==a3.c.id,
                games_table.c.black==a4.c.id))
                 
    for g in conn.execute(s):
        print "%s %s %s %s %s %s %s %s %s" % (g[0], g[1], g[2], g[3], g[4], g[5], reprResult[g[6]], g[7], g[8])

    s = select([names_table])
    names = dict([(n.id, n.name) for n in conn.execute(s)])
    print names

    sys.exit()