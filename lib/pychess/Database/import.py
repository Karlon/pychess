import os
import sys
from datetime import date

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from sqlalchemy import Table, Column, Integer, String, Date, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relation, backref

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
     event = Column(String)
     site = Column(String)
     game_date = Column(String)
     round = Column(Integer)
     white = Column(String)
     black = Column(String)
     result = Column(Integer)
     white_elo = Column(Integer)
     black_elo = Column(Integer)
     ply_count = Column(Integer)
     event_date = Column(String)
     eco = Column(String)
     fen = Column(String)
     annotator = Column(String)
     source = Column(String)

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
    
    for i, game in enumerate(cf.games):
        event = cf.get_event(i)
        site = cf.get_site(i)
        y, m, d = cf.get_date(i)
        game_date = str(date(y, m, d))
        round = cf.get_round(i)
        white, black = cf.get_player_names(i)
        result = cf.get_result(i)
        white_elo, black_elo = cf.get_elo(i)

        ply_count = 0
        event_date = ""
        eco = ""
        fen = ""
        annotator = ""
        source = ""
        movetext = game[1]

        print i, white, white_elo, black, black_elo, result, event, round, game_date, site

        load
        agame = Game(event, site, game_date, round, white, black, result, white_elo, black_elo, \
                    ply_count, event_date, eco, fen, annotator, source, movetext)

        session.add(agame)


if __name__ == "__main__":
    path = "sqlite:///" + os.path.join(addDataPrefix("pychess.db"))
    
    engine = create_engine(path, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    metadata = Base.metadata
    metadata.drop_all(engine)     
    metadata.create_all(engine)     

    load2session(sys.argv[1], session)
    
    session.commit()
    session.close()
    
    sys.exit()