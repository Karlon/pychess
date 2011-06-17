from gobject import *

from pychess.Utils.const import *
from pychess.Utils.IconLoader import load_icon
from pychess.Utils.Rating import Rating
from pychess.System.Log import log
from pychess.Variants import variants
from pychess.ic import *

class FICSPlayer (GObject):
    __gsignals__ = {
        'ratingChanged' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
    }
    def __init__ (self, name, titles=None, status=None, blitzrating=None,
                  blitzdeviation=None, stdrating=None, stddeviation=None,
                  lightrating=None, lightdeviation=None, wildrating=None,
                  wilddeviation=None, losersrating=None, losersdeviation=None):
        assert name != None
        GObject.__init__(self)
        self.name = name
        if titles == None:
            self.titles = []
        else:
            self.titles = titles
        self.status = status
        self.ratings = {}
        self.game = None
#        self.online = False
        
        for rating_type, rating, deviation in \
            ((TYPE_BLITZ, blitzrating, blitzdeviation),
             (TYPE_STANDARD, stdrating, stddeviation),
             (TYPE_LIGHTNING, lightrating, lightdeviation),
             (TYPE_WILD, wildrating, wilddeviation),
             (TYPE_LOSERS, losersrating, losersdeviation)):
            if rating and rating > 0:
                ratingobj = Rating(rating_type, rating, deviation=deviation)
                self.setRating(rating_type, ratingobj)
        
#        log.debug("FICSPlayer.init():\n")
#        log.debug("\t Initializing new player: %s\n" % repr(self))
    
    def __hash__ (self):
        """ Two players are equal if the first 10 characters of their name match.
            This is to facilitate matching players from output of commands like the 'game'
            command which only return the first 10 characters of a player's name """
        return hash(self.name[0:10].lower())
    
    def __eq__ (self, player):
        if type(self) == type(player) and self.__hash__() == player.__hash__():
            return True
        else:
            return False
        
    def __repr__ (self):
        r = "name=%s" % self.name
        if self.titles:
            r += ", titles = "
            for title in self.titles:
                r += "(" + title + ")"
        if self.status != None:
            r += ", status = %i" % self.status
        if self.game != None:
            r += ", self.game.gameno = %d" % self.game.gameno
        for rating_type in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD,
                            TYPE_LOSERS):
            if rating_type in self.ratings:
                r += ", ratings[%s] = (" % \
                    GAME_TYPES_BY_RATING_TYPE[rating_type].display_text
                r +=  self.ratings[rating_type].__repr__() + ")"
        return "<FICSPlayer " + r + ">"
    
    def isAvailableForGame (self):    
        if self.status in \
            (IC_STATUS_PLAYING, IC_STATUS_BUSY, IC_STATUS_OFFLINE,
             IC_STATUS_RUNNING_SIMUL_MATCH, IC_STATUS_NOT_AVAILABLE,
             IC_STATUS_EXAMINING, IC_STATUS_IN_TOURNAMENT):
            return False
        else:
            return True
    
    def isObservable (self):
        if self.status in (IC_STATUS_PLAYING, IC_STATUS_EXAMINING) and \
                self.game is not None and not self.game.private:
            return True
        else: return False
        
    def isGuest (self):
        if "U" in self.titles:
            return True
        else:
            return False

    def isComputer (self):    
        if "C" in self.titles:
            return True
        else:
            return False

    def isAdmin (self):    
        if "*" in self.titles:
            return True
        else:
            return False

    @classmethod
    def getIconByRating (cls, rating, size=16):
        assert type(rating) == int, "rating not an int: %s" % str(rating)
        
        if rating >= 1900:
            return load_icon(size, "weather-storm")
        elif rating >= 1600:
            return load_icon(size, "weather-showers")
        elif rating >= 1300:
            return load_icon(size, "weather-overcast")
        elif rating >= 1000:
            return load_icon(size, "weather-few-clouds")
        else:
            return load_icon(size, "weather-clear")
    
    def getIcon (self, size=16, gametype=None):
        assert type(size) == int, "size not an int: %s" % str(size)
        
        if self.isGuest():
            return load_icon(size, "stock_people", "system-users")
        elif self.isComputer():
            return load_icon(size, "computer", "stock_notebook")
        elif self.isAdmin():
            return load_icon(size, "security-high", "stock_book_blue")
        else:
            if gametype:
                rating = self.getRating(gametype.rating_type)
                rating = rating.elo if rating is not None else 0
            else:
                rating = self.getStrength()
            return self.getIconByRating(rating, size)
    
    def getMarkup (self, gametype=None):
        markup = "<big><b>%s</b></big>" % self.name
        if self.isGuest():
            markup += " <big>(%s)</big>" % _("Unregistered")
        else:
            if gametype:
                rating = self.getRating(gametype.rating_type)
                rating = rating.elo if rating is not None else 0
            else:
                rating = self.getStrength()
            if rating < 1:
                rating = _("Unrated")
            
            markup += " <big>(%s)</big>" % rating
            if self.isComputer():
                markup += " <big>(%s)</big>" % _("Computer Player")
        return markup
    
    def getTitles (self):
        r = ""
        if self.titles:
            for title in self.titles:
                r += "(" + title + ")"
        return r

    def getRating (self, rating_type):
        if rating_type in self.ratings:
            return self.ratings[rating_type]
        else:
            return None
        
    def setRating (self, rating_type, ratingobj):
        self.ratings[rating_type] = ratingobj
        
    def updateRating (self, rating_type, ratingobj):
        if rating_type in self.ratings:
            self.ratings[rating_type].update(ratingobj)
        else:
            self.setRating(rating_type, ratingobj)
        
    def addRating (self, rating_type, rating):
        if rating == None: return
        ratingobj = Rating(rating_type, rating)
        self.ratings[rating_type] = ratingobj
        
    def update (self, ficsplayer):
        assert self == ficsplayer
#        log.debug("FICSPlayer.update():\n")
#        log.debug("\t Merging ficsplayer: %s\n" % repr(ficsplayer))
#        log.debug("\t With self: %s\n" % repr(self))
        for title in ficsplayer.titles:
            if title not in self.titles:
#                log.debug("\t appending title: %s\n" % title)
                self.titles.append(title)
        if self.status != ficsplayer.status:
            self.status = ficsplayer.status
        for type in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD,
                     TYPE_LOSERS):
            if ficsplayer.ratings.has_key(type) and self.ratings.has_key(type):
                self.ratings[type].update(ficsplayer.ratings[type])
            elif ficsplayer.ratings.has_key(type):
                self.ratings[type] = ficsplayer.ratings[type]
        
    def getRatingMean (self):
        ratingtotal = 0
        numratings = 0
        for ratingtype in self.ratings:
            if self.ratings[ratingtype].deviation == None or \
               self.ratings[ratingtype].deviation == DEVIATION_NONE:
                ratingtotal += self.ratings[ratingtype].elo * 3
                numratings += 3
            if self.ratings[ratingtype].deviation == DEVIATION_ESTIMATED:
                ratingtotal += self.ratings[ratingtype].elo * 2
                numratings += 2
            if self.ratings[ratingtype].deviation == DEVIATION_PROVISIONAL:
                ratingtotal += self.ratings[ratingtype].elo * 1
                numratings += 1
        return numratings > 0 and ratingtotal / numratings or 0
    
    # FIXME: this isn't very accurate because of inflated standard ratings
    # and deflated lightning ratings and needs work
    # IDEA: use rank in addition to rating to determine strength
    def getStrength (self):
        if self.ratings.has_key(TYPE_BLITZ) and self.ratings[TYPE_BLITZ].deviation != None and \
           self.ratings[TYPE_BLITZ].deviation not in (DEVIATION_ESTIMATED, DEVIATION_PROVISIONAL):
            return self.ratings[TYPE_BLITZ].elo
        elif self.ratings.has_key(TYPE_LIGHTNING) and self.ratings[TYPE_LIGHTNING].deviation != None and \
           self.ratings[TYPE_LIGHTNING].deviation not in (DEVIATION_ESTIMATED, DEVIATION_PROVISIONAL):
            return self.ratings[TYPE_LIGHTNING].elo
        else:
            return self.getRatingMean()
    
    def getRatingForCurrentGame (self):
        if self.game == None: return None
        rating = self.getRating(self.game.game_type.rating_type)
        if rating != None:
            return rating.elo
        else:
            return None

class FICSPlayersOnline (GObject):
    __gsignals__ = {
        'FICSPlayerEntered' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayerChanged' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayerExited' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
            
    def __init__ (self, connection):
        GObject.__init__(self)
        self.players = {}
        self.connection = connection
    
    def start (self):
        self.connection.glm.connect("playerConnected", self.addPlayer)
        self.connection.glm.connect("playerDisconnected", self.delPlayer)
        self.connection.glm.connect("playerWhoI", self.addPlayer)
        self.connection.glm.connect("playerWho", self.addPlayer)
        self.connection.glm.connect("playerUnavailable", self.onPlayerUnavailable)
        self.connection.glm.connect("playerAvailable", self.addPlayer)
        self.connection.gamesinprogress.connect("FICSGameCreated", self.gameCreated)
        self.connection.gamesinprogress.connect("FICSGameEnded", self.gameEnded)

    def __getitem__ (self, player):
        if type(player) is not FICSPlayer: raise TypeError
        if hash(player) in self.players:
            return self.players[hash(player)]
        else:
            raise KeyError

    def __setitem__ (self, key_player, value_player):
        if type(key_player) is not FICSPlayer: raise TypeError
        if type(value_player) is not FICSPlayer: raise TypeError
        if key_player != value_player:
            raise Exception("Players are not the same: %s %s" % 
                            (repr(key_player), repr(value_player)))
        if hash(value_player) in self.players:
            raise Exception("Player %s already exists in %s" % 
                            (repr(value_player), str(self)))
        self.players[hash(value_player)] = value_player
    
    def __delitem__ (self, player):
        if type(player) is not FICSPlayer: raise TypeError
        if player in self:
            del self.players[hash(player)]
    
    def __contains__ (self, player):
        if type(player) is not FICSPlayer: raise TypeError
        if hash(player) in self.players:
            return True
        else:
            return False
        
    def addPlayer (self, glm, player):
#        log.debug("FICSPlayersOnline.addPlayer():\n")
        if player in self:
#            log.debug("\t player updated: " + repr(player) + "\n")
#            log.debug("\t old player: " + repr(self[player]) + "\n")
            self[player].update(player)
#            log.debug("\t new player: " + repr(self[player]) + "\n")
            self.emit('FICSPlayerChanged', self[player])
        else:
            self[player] = player
#            log.debug("player added: " + repr(self[player]) + "\n")
            self.emit('FICSPlayerEntered', self[player])
        
    def delPlayer (self, glm, player):
        if player in self:
            player = self[player]
            del self[player]
            self.emit('FICSPlayerExited', player)
    
    def gameCreated (self, gip, game):
#        log.debug("FICSPlayersOnline.gameCreated():\n")
#        log.debug("Updating players in game: %s\n" % repr(game))
        for player in (game.wplayer, game.bplayer):
            if player in self:
#                log.debug("Updating player: %s\n" % repr(player))
                self[player].status = IC_STATUS_PLAYING
                self[player].game = game
                self.emit('FICSPlayerChanged', self[player])
    
    def gameEnded (self, gip, game):
        for player in (game.wplayer, game.bplayer):
            if player in self:
                if self[player].status == IC_STATUS_PLAYING:
                    self[player].status = IC_STATUS_AVAILABLE
                self[player].game = None
                self.emit('FICSPlayerChanged', self[player])
        
    def onPlayerUnavailable (self, glm, player):
        if player in self:
            if self[player].status == IC_STATUS_AVAILABLE:
                self[player].status = player.status
                self.emit('FICSPlayerChanged', self[player])

class FICSBoard:
    def __init__ (self, wms, bms, fen=None, pgn=None):
        self.wms = wms
        self.bms = bms
        assert fen != None or pgn != None
        self.fen = fen
        self.pgn = pgn

class FICSGame (GObject):
    def __init__ (self, gameno, wplayer, bplayer, rated=False,
                  game_type=None, min=None, inc=None,
                  private=False, result=None, reason=None, board=None):
        assert type(gameno) is int, gameno
        assert isinstance(wplayer, FICSPlayer), wplayer
        assert isinstance(bplayer, FICSPlayer), bplayer
        assert game_type is None or game_type is GAME_TYPES_BY_FICS_NAME["wild"] \
            or game_type in GAME_TYPES.values(), game_type
        assert board is None or isinstance(board, FICSBoard), board
        GObject.__init__(self)
        self.gameno = gameno
        self.wplayer = wplayer
        self.bplayer = bplayer
        self.rated = rated
        self.game_type = game_type
        self.min = min  # not always set ("game created ..." message doesn't specify)
        self.inc = inc  # not always set ("game created ..." message doesn't specify)
        self.private = private
        self.result = result
        self.reason = reason
        self.board = board
        
    def __eq__ (self, game):
        if type(self) == type(game) and self.gameno == game.gameno \
           and self.wplayer == game.wplayer and self.bplayer == game.bplayer:
            return True
        else:
            return False
    
    def __repr__ (self):
        r = "<FICSGame gameno=%s, wplayer={%s}, bplayer={%s}" % \
            (self.gameno, repr(self.wplayer), repr(self.bplayer))
        r += self.rated and ", rated=True" or ", rated=False"
        r += ", game_type=%s" % self.game_type
        r += self.private and ", private=True" or ", private=False"
        if self.min != None:
            r += ", min=%i" % self.min
        if self.inc != None:
            r += ", inc=%i" % self.inc
        if self.result != None:
            r += ", result=%i" % self.result
        if self.reason != None:
            r += ", reason=%i>" % self.reason
        return r

class FICSGamesInProgress (GObject):
    __gsignals__ = {
        'FICSGameCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSGameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayGameCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayGameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSObsGameCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSObsGameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.games = {}
        self.connection = connection

    def start (self):
        self.connection.glm.connect("addGame", self.addGame)
        self.connection.bm.connect("playGameCreated", self.playGameCreated)
        self.connection.bm.connect("obsGameCreated", self.obsGameCreated)
        self.connection.glm.connect("removeGame", self.removeGame)

    def __getitem__ (self, gameno):
        if gameno in self.games:
            return self.games[gameno]
        else:
            raise KeyError
    
    def addGame (self, glm, game):
#        log.debug("FICSGamesInProgress.addGame():\n")
#        log.debug("\t Adding game: %s\n" % repr(game))
        if game.wplayer in self.connection.playersonline:
#            log.debug("\t Found wplayer in playersonline: %s\n" \
#                      % repr(self.connection.playersonline[game.wplayer]))
            game.wplayer = self.connection.playersonline[game.wplayer]
        else:
#            log.debug("\t Adding game.wplayer to playersonline: %s\n" % repr(game.wplayer))
            self.connection.playersonline.addPlayer(glm, game.wplayer)
        if game.bplayer in self.connection.playersonline:
#            log.debug("\t Found bplayer in playersonline: %s\n" \
#                      % repr(self.connection.playersonline[game.bplayer]))
            game.bplayer = self.connection.playersonline[game.bplayer]
        else:
#            log.debug("\t Adding game.bplayer to playersonline: %s\n" % repr(game.bplayer))
            self.connection.playersonline.addPlayer(glm, game.bplayer)
        if game.gameno not in self.games:
            self.games[game.gameno] = game
            self.emit('FICSGameCreated', game)
        
    def removeGame (self, glm, game):
        if game.gameno in self.games:
            game = self.games[game.gameno]
            del self.games[game.gameno]
            self.emit('FICSGameEnded', game)
    
    def playGameCreated (self, glm, game):
        self.addGame(glm, game)
        self.emit('FICSPlayGameCreated', game)
    
    def obsGameCreated (self, glm, game):
        self.addGame(glm, game)
        self.emit('FICSObsGameCreated', game)

class FICSSeek:
    def __init__ (self, name, min, inc, rated, color, game_type, rmin=0, rmax=9999):
        assert game_type in GAME_TYPES, game_type
        self.seeker = name
        self.min = min
        self.inc = inc
        self.rated = rated
        self.color = color
        self.game_type = game_type
        self.rmin = rmin  # minimum rating one has to have to be offered this seek
        self.rmax = rmax  # maximum rating one has to have to be offered this seek
        
#
#if __name__ == "main":
#    def