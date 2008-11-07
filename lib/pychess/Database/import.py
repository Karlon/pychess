import os
import sys
from datetime import date

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from profilehooks import profile

from sqlalchemy import Table, Column, Integer, String, Date, create_engine, ForeignKey, MetaData, select

from pychess.Utils.const import *
from pychess.Savers.pgn import load
from pychess.System.prefix import addDataPrefix


metadata = MetaData()

name = Table('names', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String)
    )

game = Table('games', metadata,
    Column('id', Integer, primary_key=True),
    Column('event', Integer, ForeignKey('names.id')),
    Column('site', Integer, ForeignKey('names.id')),
    Column('game_date', Date),
    Column('round', Integer),
    Column('white', Integer, ForeignKey('names.id')),
    Column('black', Integer, ForeignKey('names.id')),
    Column('result', String(1)),
    Column('white_elo', Integer),
    Column('black_elo', Integer),
    Column('ply_count', Integer),
    Column('event_date', Date),
    Column('eco', String(3)),
    Column('fen', String),
    Column('annotator', Integer, ForeignKey('names.id')),
    Column('source', Integer, ForeignKey('names.id')),
    Column('movetext', String)
    )


#@profile
def import_from_pgn(file, conn, game_table, name_table):
    cf = load(open(file))
    
    s = select([name_table])
    names = dict([(n.name, n.id) for n in conn.execute(s)])

    def get_id(name_str):
        if not name_str:
            return None

        if name_str in names:
            return names[name_str]
        else:
            ins_name = name_table.insert()
            result = conn.execute(ins_name, name=name_str)
            id = result.last_inserted_ids()[0]
            names[name_str] = id
            return id
    
    for i, game in enumerate(cf.games):
        event = get_id(cf.get_event(i))
        site = get_id(cf.get_site(i))
        y, m, d = cf.get_date(i)
        game_date = date(y, m, d)
        round = cf.get_round(i)
        white, black = cf.get_player_names(i)
        white = get_id(white)
        black = get_id(black)
        result = reprResult[cf.get_result(i)]
        white_elo, black_elo = cf.get_elo(i)

        ply_count = cf._getTag(i, "PlyCount")
        y, m, d = cf.get_event_date(i)
        event_date = date(y, m, d)
        eco = cf._getTag(i, "ECO")
        fen = cf._getTag(i, "FEN")
        annotator = get_id(cf._getTag(i, "Annotator"))
        source = get_id(cf._getTag(i, "Source"))
        movetext = game[1]

#        print i, event, site, game_date, round, white, black, result
        ins_game = game_table.insert()
        result = conn.execute(ins_game,
                                event=event,
                                site=site,
                                game_date=game_date,
                                round=round,
                                white=white,
                                black=black,
                                result=result,
                                white_elo=white_elo,
                                black_elo=black_elo,
                                ply_count=ply_count,
                                event_date=event_date,
                                eco=eco,
                                fen=fen,
                                annotator=annotator,
                                source=source,
                                movetext=movetext)


if __name__ == "__main__":
    path = "sqlite:///" + os.path.join(addDataPrefix("pychess.db"))
    
    engine = create_engine(path, echo=True)
    
    metadata.drop_all(engine)     
    metadata.create_all(engine)     

    conn = engine.connect()

    import_from_pgn(sys.argv[1], conn, game, name)
    
    s = select([name])
    names = dict([(n.id, n.name) for n in conn.execute(s)])
    print names
    
    s = select([game])
    for g in conn.execute(s):
        print g[0:7]
    
    sys.exit()