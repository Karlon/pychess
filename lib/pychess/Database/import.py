import os
import sys
from datetime import date

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, Date, create_engine, ForeignKey

from pychess.Utils.const import *
from pychess.Savers.pgn import load
from pychess.System.prefix import addDataPrefix


Base = declarative_base()


class Name(Base):
     __tablename__ = 'names'

     id = Column(Integer, primary_key=True)
     name = Column(String)

     def __init__(self, name):
         self.name = name

     def __repr__(self):
        return "<Name('%s')>" % self.name


class Game(Base):
     __tablename__ = 'games'

     id = Column(Integer, primary_key=True)
     event = Column(Integer, ForeignKey('names.id'))
     site = Column(Integer, ForeignKey('names.id'))
     game_date = Column(Date)
     round = Column(Integer)
     white = Column(Integer, ForeignKey('names.id'))
     black = Column(Integer, ForeignKey('names.id'))
     result = Column(String(1))
     white_elo = Column(Integer)
     black_elo = Column(Integer)
     ply_count = Column(Integer)
     event_date = Column(Date)
     eco = Column(String(3))
     fen = Column(String)
     annotator = Column(Integer, ForeignKey('names.id'))
     source = Column(Integer, ForeignKey('names.id'))

     movetext = Column(String)

     def __init__(self, event, site, game_date, round, white, black, result, white_elo, black_elo, \
                    ply_count, event_date, eco, fen, annotator, source, movetext):
        self.event = event
        self.site = site
        self.game_date = game_date
        self.round = round
        self.white = white
        self.black = black
        self.result = result
        self.white_elo = white_elo
        self.black_elo = black_elo
        self.ply_count = ply_count
        self.event_date = event_date
        self.eco = eco
        self.fen = fen
        self.annotator = annotator
        self.source = source
        self.movetext = movetext

     def __repr__(self):
        return "<Game('%s', '%s', '%s', '%s', '%s', '%s', '%s')>" % \
            (self.event, self.site, self.game_date, self.round, self.white, self.black, self.result)


def load2session(file, session):
    cf = load(open(file))
    
    names = [(n.name, n.id) for n in session.query(Name)]
    names = dict(names)

    def get_id(name):
        if not name:
            return None

        if name in names:
            return names[name]
        else:
            new_name = Name(name)
            session.add(new_name)
            session.commit()
            names[name] = new_name.id
            return names[name]
    
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

        print i, event, site, game_date, round, white, black, result
        agame = Game(event, site, game_date, round, white, black, result, white_elo, black_elo, \
                    ply_count, event_date, eco, fen, annotator, source, movetext)

        session.add(agame)


if __name__ == "__main__":
    path = "sqlite:///" + os.path.join(addDataPrefix("pychess.db"))
    
    engine = create_engine(path, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    metadata = Base.metadata
    metadata.drop_all(engine)     
    metadata.create_all(engine)     

    load2session(sys.argv[1], session)
    
    session.commit()

    names = [(n.id, n.name) for n in session.query(Name)]
    names = dict(names)
    for g in session.query(Game):
        print g.id, g.game_date, names[g.white], names[g.black], g.result, names[g.event], g.ply_count, g.eco
    
    session.close()
    
    sys.exit()