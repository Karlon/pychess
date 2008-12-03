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
    Column('id', Integer, Sequence('names_id_seq', optional=True), primary_key=True),
    Column('name', String(256))
    )

games_table = Table('games', metadata,
    Column('id', Integer, Sequence('games_id_seq', optional=True), primary_key=True),
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
    Column('white_title', CHAR(3)),
    Column('black_title', CHAR(3)),
    Column('ply_count', SmallInteger),
    Column('eco', CHAR(3)),
    Column('board', SmallInteger),
    Column('fen', String(128)),
    Column('annotator', Integer, ForeignKey('names.id')),
    Column('source', Integer, ForeignKey('names.id')),
    Column('movetext', String)
    )

class PgnImport():
    def __init__(self):
        self.ins_names = names_table.insert()
        self.ins_games = games_table.insert()
        
        self.names = {}
        self.nextid = None

        # collect new names not in names dict yet
        self.name_data = []
        # collect new games and commit them in big chunks for speed
        self.game_data = []

    def get_id(self, name):
        if not name:
            return None

        if name in self.names:
            return self.names[name]
        else:
            self.name_data.append({'name':name})
            self.names[name] = self.nextid
            self.nextid += 1
            return self.names[name]

    #@profile
    def do_import(self, file, conn):
        cf = load(open(file))

        # initialise names dict to speed up lookup of names
        s = select([names_table])
        self.names = dict([(n.name, n.id) for n in conn.execute(s)])

        # get the names_id_seq or bigest names.id to use it for manual increment
        self.nextid = conn.execute(Sequence('names_id_seq', optional=True))
        if self.nextid:
            self.nextid += 1
        else:
            s = select([func.max(names_table.c.id).label('maxid')])
            maxid = conn.execute(s).scalar()
            if maxid is None:
                self.nextid = 1
            else:
                self.nextid = maxid + 1

        # use transaction to avoid autocommit slowness
        trans = conn.begin()
        try:
            for i, game in enumerate(cf.games):
                event = self.get_id(cf._getTag(i, 'Event'))
                site = self.get_id(cf._getTag(i, 'Site'))
                game_date = cf._getTag(i, 'Date')
                if game_date and not '?' in game_date:
                    ymd = game_date.split('.')
                    if len(ymd) == 3:
                        game_year, game_month, game_day = map(int, ymd)
                    else:
                        game_year, game_month, game_day = int(game_date[:4]), None, None
                elif game_date and not '?' in game_date[:4]:
                    game_year, game_month, game_day = int(game_date[:4]), None, None
                else:
                    game_year, game_month, game_day = None, None, None
                try:
                    round = int(cf._getTag(i, 'Round'))
                except:
                    round = None
                white, black = cf.get_player_names(i)
                white = self.get_id(white)
                black = self.get_id(black)
                result = cf.get_result(i)
                try:
                    white_elo = int(cf._getTag(i, 'WhiteElo'))
                    black_elo = int(cf._getTag(i, 'BlackElo'))
                except:
                    white_elo = None
                    black_elo = None
                ply_count = cf._getTag(i, "PlyCount")
                event_date = cf._getTag(i, 'EventDate')
                eco = cf._getTag(i, "ECO")
                if eco:
                    eco = eco[:3]
                fen = cf._getTag(i, "FEN")
                annotator = self.get_id(cf._getTag(i, "Annotator"))
                source = self.get_id(cf._getTag(i, "Source"))
                movetext = game[1]
                
                if len(self.game_data) < CHUNK:
                    self.game_data.append({
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
                    if self.name_data:
                        conn.execute(self.ins_names, self.name_data)
                        self.name_data = []

                    conn.execute(self.ins_games, self.game_data)
                    self.game_data = []
                    print file, CHUNK
                
            if self.name_data:
                conn.execute(self.ins_names, self.name_data)
                self.name_data = []

            if self.game_data:
                conn.execute(self.ins_games, self.game_data)
                self.game_data = []

            print file, i+1
            trans.commit()
        except:
            trans.rollback()
            print "File %s had errors. Not imported!" % file
            raise

def print_db(conn):
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
                 
    for g in conn.execute(s):
        print "%s %s %s %s %s %s %s %s %s %s %s" % (g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7], reprResult[g[8]], g[9], g[10])

    s = select([names_table])
    names = dict([(n.id, n.name) for n in conn.execute(s)])
    print names


if __name__ == "__main__":
    # TODO: make the dbdriver configurable
    #path = "sqlite:///" + os.path.join(addDataPrefix("pychess.pdb"))
    path = "firebird://sysdba:masterkey@localhost//home/tamas/data/pychess.fdb"
    
    engine = create_engine(path, echo=False)
    conn = engine.connect()

    metadata.drop_all(engine)
    metadata.create_all(engine)

    imp = PgnImport()
    arg = sys.argv[1]
    if arg[-3:].lower() == "pgn":
        imp.do_import(arg, conn)
    elif os.path.exists(arg):
        for file in os.listdir(arg):
            if file[-3:].lower() == "pgn":
                imp.do_import(file, conn)

    print_db(conn)
    
    sys.exit()