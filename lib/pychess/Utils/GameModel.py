from collections import defaultdict
from threading import RLock
import traceback
import cStringIO
import datetime
import Queue

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

from pychess.Savers.ChessFile import LoadingError
from pychess.Players.Player import PlayerIsDead, TurnInterrupt
from pychess.System.ThreadPool import PooledThread, pool
from pychess.System.protoopen import protoopen, protosave, isWriteable
from pychess.System.Log import log
from pychess.System import conf
from pychess.Utils.Move import Move, toSAN
from pychess.Utils.eco import get_eco
from pychess.Variants.normal import NormalChess
from pychess.Variants import variants

from logic import getStatus, isClaimableDraw, playerHasMatingMaterial
from const import *

def undolocked (f):
    def newFunction(*args, **kw):
        self = args[0]
        log.debug("undolocked: adding func to queue: %s %s %s\n" % \
            (repr(f), repr(args), repr(kw)))
        self.undoQueue.put((f, args, kw))
        
        locked = self.undoLock.acquire(blocking=False)        
        if locked:
            try:
                while True:
                    try:
                        func, args, kw = self.undoQueue.get_nowait()
                        log.debug("undolocked: running queued func: %s %s %s\n" % \
                            (repr(func), repr(args), repr(kw)))
                        func(*args, **kw)
                    except Queue.Empty:
                        break
            finally:
                self.undoLock.release()
    return newFunction

def inthread (f):
    def newFunction(*args, **kw):
        pool.start(f, *args, **kw)
    return newFunction

class GameModel (GObject, PooledThread):
    
    """ GameModel contains all available data on a chessgame.
        It also has the task of controlling players actions and moves """
    
    __gsignals__ = {
        # game_started is emitted when control is given to the players for the
        # first time. Notice this is after players.start has been called.
        "game_started":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # game_changed is emitted when a move has been made.
        "game_changed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # moves_undoig is emitted when a undoMoves call has been accepted, but
        # before anywork has been done to execute it.
        "moves_undoing": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        # moves_undone is emitted after n moves have been undone in the
        # gamemodel and the players.
        "moves_undone":  (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        # game_unended is emitted if moves have been undone, such that the game
        # which had previously ended, is now again active.
        "game_unended":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # game_loading is emitted if the GameModel is about to load in a chess
        # game from a file. 
        "game_loading":  (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        # game_loaded is emitted after the chessformat handler has loaded in
        # all the moves from a file to the game model.
        "game_loaded":   (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        # game_saved is emitted in the end of model.save()
        "game_saved":    (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        # game_ended is emitted if the models state has been changed to an
        # "ended state"
        "game_ended":    (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        # game_terminated is emitted if the game was terminated. That is all
        # players and clocks were stopped, and it is no longer possible to
        # resume the game, even by undo.
        "game_terminated":    (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # game_paused is emitted if the game was successfully paused.
        "game_paused":   (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # game_paused is emitted if the game was successfully resumed from a
        # pause.
        "game_resumed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # action_error is currently only emitted by ICGameModel, in the case
        # the "web model" didn't accept the action you were trying to do.
        "action_error":  (SIGNAL_RUN_FIRST, TYPE_NONE, (object, int)),
        # players_changed is emitted if the players list was changed.
        "players_changed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "analyzer_added": (SIGNAL_RUN_FIRST, None, (object, str)),
        "analyzer_removed": (SIGNAL_RUN_FIRST, None, (object, str)),
        "analyzer_paused": (SIGNAL_RUN_FIRST, None, (object, str)),
        "analyzer_resumed": (SIGNAL_RUN_FIRST, None, (object, str)),
        # opening_changed is emitted if the move changed the opening.
        "opening_changed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        # variations_changed is emitted if a variation was added/deleted.
        "variations_changed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
    }
    
    def __init__ (self, timemodel=None, variant=NormalChess):
        GObject.__init__(self)

        self.variant = variant
        self.boards = [variant.board(setup=True)]
        
        self.moves = []
        self.players = []
        
        self.gameno = 0
        self.variations = [self.boards]
        
        self.status = WAITING_TO_START
        self.reason = UNKNOWN_REASON
        
        self.timemodel = timemodel
        
        self.connections = defaultdict(list)  # mainly for IC subclasses
        
        now = datetime.datetime.now()
        self.tags = {
            "Event": _("Local Event"),
            "Site":  _("Local Site"),
            "Round": 1,
            "Year":  now.year,
            "Month": now.month,
            "Day":   now.day,
            "Time":  "%02d:%02d:00" % (now.hour, now.minute),
            "Result": "*",
        }

        if self.timemodel:
            self.tags["TimeControl"] = \
                "%d+%d" % (self.timemodel.minutes*60, self.timemodel.gain)
            # Notice: tags["WhiteClock"] and tags["BlackClock"] are never set
            # on the gamemodel, but simply written or read during saving/
            # loading from pgn. If you want to know the time left for a player,
            # check the time model.
        
        # Keeps track of offers, so that accepts can be spotted
        self.offers = {}
        # True if the game has been changed since last save
        self.needsSave = False
        # The uri the current game was loaded from, or None if not a loaded game
        self.uri = None
        
        self.spectators = {}
        
        self.applyingMoveLock = RLock()
        self.undoLock = RLock()
        self.undoQueue = Queue.Queue()
    
    def __repr__ (self):
        s = "<GameModel at %s" % id(self)
        s += " (ply=%s" % self.ply
        if len(self.moves) > 0:
            s += ", move=%s" % self.moves[-1]
        s += ", variant=%s" % self.variant.name
        s += ", status=%s, reason=%s" % (str(self.status), str(self.reason))
        s += ", players=%s" % str(self.players)
        s += ", tags=%s" % str(self.tags)
        if len(self.boards) > 0:
            s += "\nboard=%s" % self.boards[-1]
        return s + ")>"
    
    @property
    def display_text (self):
        if self.variant == NormalChess and self.timemodel is None:
            return "[ " + _("Untimed") + " ]"
        else:
            t = "[ "
            if self.variant != NormalChess:
                t += self.variant.name + " "
            if self.timemodel is not None:
                t += self.timemodel.display_text + " "
            return t + "]"
        
    def setPlayers (self, players):
        assert self.status == WAITING_TO_START
        self.players = players
        for player in self.players:
            self.connections[player].append(player.connect("offer", self.offerRecieved))
            self.connections[player].append(player.connect("withdraw", self.withdrawRecieved))
            self.connections[player].append(player.connect("decline", self.declineRecieved))
            self.connections[player].append(player.connect("accept", self.acceptRecieved))
        self.tags["White"] = str(self.players[WHITE])
        self.tags["Black"] = str(self.players[BLACK])
        self.emit("players_changed")
    
    def start_analyzer (self, analyzer_type):
        from pychess.Players.engineNest import init_engine
        analyzer = init_engine(analyzer_type, self)
        if analyzer is None: return
        
        analyzer.setOptionInitialBoard(self)
        self.spectators[analyzer_type] = analyzer
        self.emit("analyzer_added", analyzer, analyzer_type)
        return analyzer
    
    def remove_analyzer (self, analyzer_type):
        try:
            analyzer = self.spectators[analyzer_type]
        except KeyError:
            return
        
        analyzer.end(KILLED, UNKNOWN_REASON)
        self.emit("analyzer_removed", analyzer, analyzer_type)
        del self.spectators[analyzer_type]
        
    def resume_analyzer (self, analyzer_type):
        try:
            analyzer = self.spectators[analyzer_type]
        except KeyError:
            analyzer = self.start_analyzer(analyzer_type)
            if analyzer is None: return
        
        analyzer.resume()
        analyzer.setOptionInitialBoard(self)
        self.emit("analyzer_resumed", analyzer, analyzer_type)
    
    def pause_analyzer (self, analyzer_type):
        try:
            analyzer = self.spectators[analyzer_type]
        except KeyError:
            return
        
        analyzer.pause()
        self.emit("analyzer_paused", analyzer, analyzer_type)
        
    def restart_analyzer (self, analyzer_type):
        self.remove_analyzer(analyzer_type)
        self.start_analyzer(analyzer_type)
    
    def setOpening(self):
        if self.ply > 40:
            return

        if self.ply > 0:
            opening = get_eco(self.getBoardAtPly(self.ply).board.hash)
        else:
            opening = ("", "", "")
        if opening is not None:
            self.tags["ECO"] = opening[0]
            self.tags["Opening"] = opening[1]
            self.tags["Variation"] = opening[2]
            self.emit("opening_changed")
    
    ############################################################################
    # Board stuff                                                              #
    ############################################################################
    
    def _get_ply (self):
        return self.boards[-1].ply
    ply = property(_get_ply)
    
    def _get_lowest_ply (self):
        return self.boards[0].ply
    lowply = property(_get_lowest_ply)
    
    def _get_curplayer (self):
        try:
            return self.players[self.getBoardAtPly(self.ply).color]
        except IndexError:
            log.error("%s %s\n" % (self.players, self.getBoardAtPly(self.ply).color))
            raise
    curplayer = property(_get_curplayer)
    
    def _get_waitingplayer (self):
        try:
            return self.players[1 - self.getBoardAtPly(self.ply).color]
        except IndexError:
            log.error("%s %s\n" % (self.players, 1 - self.getBoardAtPly(self.ply).color))
            raise
    waitingplayer = property(_get_waitingplayer)
    
    def _plyToIndex (self, ply):
        index = ply - self.lowply
        if index < 0:
            raise IndexError, "%s < %s\n" % (ply, self.lowply)
        return index
    
    def getBoardAtPly (self, ply, variation=0):
        try:
            return self.variations[variation][self._plyToIndex(ply)]
        except:
            log.error("%d\t%d\t%d\t%d\n" % (self.lowply, ply, self.ply, len(self.variations[variation])))
            raise
    
    def getMoveAtPly (self, ply, variation=0):
        try:
            return Move(self.variations[variation][self._plyToIndex(ply)+1].board.lastMove)
        except IndexError:
            log.error("%d\t%d\t%d\t%d\n" % (self.lowply, ply, self.ply, len(self.moves)))
            raise
    
    def isObservationGame (self):
        if self.players[0].__type__ == LOCAL or self.players[1].__type__ == LOCAL:
            return False
        else:
            return True

    def isEngine2EngineGame (self):
        if self.players[0].__type__ == ARTIFICIAL and self.players[1].__type__ == ARTIFICIAL:
            return True
        else:
            return False

    ############################################################################
    # Offer management                                                         #
    ############################################################################
    
    def offerRecieved (self, player, offer):
        log.debug("GameModel.offerRecieved: offerer=%s %s\n" % (repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer.type == HURRY_ACTION:
            opPlayer.hurry()
        
        elif offer.type == CHAT_ACTION:
            opPlayer.putMessage(offer.param)
        
        elif offer.type == RESIGNATION:
            if player == self.players[WHITE]:
                self.end(BLACKWON, WON_RESIGN)
            else: self.end(WHITEWON, WON_RESIGN)
        
        elif offer.type == FLAG_CALL:
            assert self.timemodel is not None            
            if self.timemodel.getPlayerTime(1-player.color) <= 0:
                if self.timemodel.getPlayerTime(player.color) <= 0:
                    self.end(DRAW, DRAW_CALLFLAG)
                elif not playerHasMatingMaterial(self.boards[-1], 1-player.color):
                    if 1-player.color == WHITE:
                        self.end(DRAW, DRAW_BLACKINSUFFICIENTANDWHITETIME)
                    else:
                        self.end(DRAW, DRAW_WHITEINSUFFICIENTANDBLACKTIME)
                else:
                    if player == self.players[WHITE]:
                        self.end(WHITEWON, WON_CALLFLAG)
                    else:
                        self.end(BLACKWON, WON_CALLFLAG)
            else:
                player.offerError(offer, ACTION_ERROR_NOT_OUT_OF_TIME)
        
        elif offer.type == DRAW_OFFER and isClaimableDraw(self.boards[-1]):
            reason = getStatus(self.boards[-1])[1]
            self.end(DRAW, reason)
        
        elif offer.type == TAKEBACK_OFFER and offer.param < self.lowply:
            player.offerError(offer, ACTION_ERROR_TOO_LARGE_UNDO)
        
        elif offer.type in OFFERS:
            if offer not in self.offers:
                log.debug("GameModel.offerRecieved: doing %s.offer(%s)\n" % \
                    (repr(opPlayer), offer))
                self.offers[offer] = player
                opPlayer.offer(offer)
            # If we updated an older offer, we want to delete the old one
            for offer_ in self.offers.keys():
                if offer.type == offer_.type and offer != offer_:
                    del self.offers[offer_]
    
    def withdrawRecieved (self, player, offer):
        log.debug("GameModel.withdrawRecieved: withdrawer=%s %s\n" % \
            (repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offers and self.offers[offer] == player:
            del self.offers[offer]
            opPlayer.offerWithdrawn(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_WITHDRAW)
    
    def declineRecieved (self, player, offer):
        log.debug("GameModel.declineRecieved: decliner=%s %s\n" % (repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offers and self.offers[offer] == opPlayer:
            del self.offers[offer]
            log.debug("GameModel.declineRecieved: declining %s\n" % offer)
            opPlayer.offerDeclined(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_DECLINE)
    
    def acceptRecieved (self, player, offer):
        log.debug("GameModel.acceptRecieved: accepter=%s %s\n" % (repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offers and self.offers[offer] == opPlayer:
            if offer.type == DRAW_OFFER:
                self.end(DRAW, DRAW_AGREE)
            elif offer.type == TAKEBACK_OFFER:
                log.debug("GameModel.acceptRecieved: undoMoves(%s)\n" % \
                    (self.ply - offer.param))
                self.undoMoves(self.ply - offer.param)
            elif offer.type == ADJOURN_OFFER:
                self.end(ADJOURNED, ADJOURNED_AGREEMENT)
            elif offer.type == ABORT_OFFER:
                self.end(ABORTED, ABORTED_AGREEMENT)
            elif offer.type == PAUSE_OFFER:
                self.pause()
            elif offer.type == RESUME_OFFER:
                self.resume()
            del self.offers[offer]
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)
    
    ############################################################################
    # Data stuff                                                               #
    ############################################################################
    
    def loadAndStart (self, uri, loader, gameno, position):
        assert self.status == WAITING_TO_START

        uriIsFile = type(uri) != str
        if not uriIsFile:
            chessfile = loader.load(protoopen(uri))
        else: 
            chessfile = loader.load(uri)
        
        self.gameno = gameno
        self.emit("game_loading", uri)
        try:
            chessfile.loadToModel(gameno, position, self)
        #Postpone error raising to make games loadable to the point of the error
        except LoadingError, e:
            error = e
        else: error = None
        if self.players:
            self.players[WHITE].setName(self.tags["White"])
            self.players[BLACK].setName(self.tags["Black"])
        self.emit("game_loaded", uri)
        
        self.needsSave = False
        if not uriIsFile:
            self.uri = uri
        else: self.uri = None
        
        # Even if the game "starts ended", the players should still be moved
        # to the last position, so analysis is correct, and a possible "undo"
        # will work as expected. 
        for spectator in self.spectators.values():
            spectator.setOptionInitialBoard(self)
        for player in self.players:
            player.setOptionInitialBoard(self)
        if self.timemodel:
            self.timemodel.setMovingColor(self.boards[-1].color)
        
        if self.status == RUNNING:
            if self.timemodel and self.ply >= 2:
                self.timemodel.start()
            
        self.status = WAITING_TO_START
        self.start()
        
        if error:
            raise error
    
    def save (self, uri, saver, append):
        if type(uri) == str:
            fileobj = protosave(uri, append)
            self.uri = uri
        else:
            fileobj = uri
            self.uri = None
        saver.save(fileobj, self)
        self.emit("game_saved", uri)
        self.needsSave = False
        
    ############################################################################
    # Run stuff                                                                #
    ############################################################################
    
    def run (self):
        log.debug("GameModel.run: Starting. self=%s\n" % self)
        # Avoid racecondition when self.start is called while we are in self.end
        if self.status != WAITING_TO_START:
            return
        self.status = RUNNING
        
        for player in self.players + self.spectators.values():
            player.start()
        
        log.debug("GameModel.run: emitting 'game_started' self=%s\n" % self)
        self.emit("game_started")
        
        # Let GameModel end() itself on games started with loadAndStart()
        self.checkStatus()
        
        while self.status in (PAUSED, RUNNING, DRAW, WHITEWON, BLACKWON):
            curColor = self.boards[-1].color
            curPlayer = self.players[curColor]
            
            if self.timemodel:
                log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: updating %s's time\n" % \
                    (id(self), str(self.players), str(self.ply), str(curPlayer)))
                curPlayer.updateTime(self.timemodel.getPlayerTime(curColor),
                                     self.timemodel.getPlayerTime(1-curColor))
            
            try:
                log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: calling %s.makeMove()\n" % \
                    (id(self), str(self.players), self.ply, str(curPlayer)))
                if self.ply > self.lowply:
                    move = curPlayer.makeMove(self.boards[-1],
                                              self.moves[-1],
                                              self.boards[-2])
                else: move = curPlayer.makeMove(self.boards[-1], None, None)
                log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: got move=%s from %s\n" % \
                    (id(self), str(self.players), self.ply, move, str(curPlayer)))
            except PlayerIsDead, e:
                if self.status in (WAITING_TO_START, PAUSED, RUNNING):
                    stringio = cStringIO.StringIO()
                    traceback.print_exc(file=stringio)
                    error = stringio.getvalue()
                    log.error("GameModel.run: A Player died: player=%s error=%s\n%s" % (curPlayer, error, e))
                    if curColor == WHITE:
                        self.kill(WHITE_ENGINE_DIED)
                    else: self.kill(BLACK_ENGINE_DIED)
                break
            except TurnInterrupt:
                log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: TurnInterrupt\n" % \
                    (id(self), str(self.players), self.ply))
                continue
            
            log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: acquiring self.applyingMoveLock\n" % \
                (id(self), str(self.players), self.ply))
            assert isinstance(move, Move), "%s" % repr(move)
            self.applyingMoveLock.acquire()
            try:
                log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: applying move=%s\n" % \
                    (id(self), str(self.players), self.ply, str(move)))
                self.needsSave = True
                newBoard = self.boards[-1].move(move, show_captured=conf.get("showCaptured", False))
                newBoard.board.prev = self.boards[-1].board
                
                # Variation on next move can exist from the hint panel...
                if self.boards[-1].board.next is not None:
                    newBoard.board.children = self.boards[-1].board.next.children
                
                self.boards = self.variations[0]
                self.boards[-1].board.next = newBoard.board
                self.boards.append(newBoard)
                self.moves.append(move)

                if self.timemodel:
                    self.timemodel.tap()
                
                self.checkStatus()
                
                self.emit("game_changed")
                
                for spectator in self.spectators.values():
                    spectator.putMove(self.boards[-1], self.moves[-1], self.boards[-2])

                self.setOpening()

            finally:
                log.debug("GameModel.run: releasing self.applyingMoveLock\n")
                self.applyingMoveLock.release()
    
    def checkStatus (self):
        """ Updates self.status so it fits with what getStatus(boards[-1])
            would return. That is, if the game is e.g. check mated this will
            call mode.end(), or if moves have been undone from an otherwise
            ended position, this will call __resume and emit game_unended. """
         
        log.debug("GameModel.checkStatus:\n")
        status, reason = getStatus(self.boards[-1])
         
        if status != RUNNING and self.status in (WAITING_TO_START, PAUSED, RUNNING):
            engine_engine = self.players[WHITE].__type__ == ARTIFICIAL and self.players[BLACK].__type__ == ARTIFICIAL
            if status == DRAW and reason in (DRAW_REPITITION, DRAW_50MOVES):
                if engine_engine:
                    self.end(status, reason)
                    return
            else:
                self.end(status, reason)
                return
        
        if status != self.status and self.status in UNDOABLE_STATES \
                and self.reason in UNDOABLE_REASONS:
            self.__resume()
            self.status = status
            self.reason = UNKNOWN_REASON
            self.emit("game_unended")
   
    def __pause (self):
        log.debug("GameModel.__pause: %s\n" % self)
        for player in self.players:
            player.pause()
        if self.timemodel:
            self.timemodel.pause()
    
    @inthread
    def pause (self):
        """ Players will raise NotImplementedError if they doesn't support
            pause. Spectators will be ignored. """
        
        self.applyingMoveLock.acquire()
        try:
            self.__pause()
            self.status = PAUSED
        finally:
            self.applyingMoveLock.release()
        self.emit("game_paused")
    
    def __resume (self):
        for player in self.players:
            player.resume()
        if self.timemodel:
            self.timemodel.resume()
        self.emit("game_resumed")
    
    @inthread
    def resume (self):
        self.applyingMoveLock.acquire()
        try:
            self.status = RUNNING
            self.__resume()
        finally:
            self.applyingMoveLock.release()
    
    def end (self, status, reason):
        if self.status not in UNFINISHED_STATES:
            log.log("GameModel.end: Can't end a game that's already ended: %s %s\n" % (status, reason))
            return
        if self.status not in (WAITING_TO_START, PAUSED, RUNNING):
            self.needsSave = True
        
        #log.debug("Ending a game with status %d for reason %d\n%s" % (status, reason,
        #    "".join(traceback.format_list(traceback.extract_stack())).strip()))
        log.debug("GameModel.end: players=%s, self.ply=%s: Ending a game with status %d for reason %d\n" % \
            (repr(self.players), str(self.ply), status, reason))
        self.status = status
        self.reason = reason
        
        self.emit("game_ended", reason)
        
        self.__pause()
    
    def kill (self, reason):
        log.debug("GameModel.kill: players=%s, self.ply=%s: Killing a game for reason %d\n%s" % \
            (repr(self.players), str(self.ply), reason,
             "".join(traceback.format_list(traceback.extract_stack())).strip()))
        
        self.status = KILLED
        self.reason = reason
        
        for player in self.players:
            player.end(self.status, reason)
        
        for spectator in self.spectators.values():
            spectator.end(self.status, reason)
        
        if self.timemodel:
            self.timemodel.end()
        
        self.emit("game_ended", reason)
    
    def terminate (self):
        
        if self.status != KILLED:
            #self.resume()
            for player in self.players:
                player.end(self.status, self.reason)
            
            for spectator in self.spectators.values():
                spectator.end(self.status, self.reason)
            
            if self.timemodel:
                self.timemodel.end()
        
        self.emit("game_terminated")
    
    ############################################################################
    # Other stuff                                                              #
    ############################################################################
    
    @inthread
    @undolocked
    def undoMoves (self, moves):
        """ Undo and remove moves number of moves from the game history from
            the GameModel, players, and any spectators """
        if self.ply < 1 or moves < 1: return
        if self.ply - moves < 0:
            # There is no way in the current threaded/asynchronous design
            # for the GUI to know that the number of moves it requests to takeback
            # will still be valid once the undo is actually processed. So, until
            # we either add some locking or get a synchronous design, we quietly
            # "fix" the takeback request rather than cause AssertionError or IndexError  
            moves = 1
        
        log.debug("GameModel.undoMoves: players=%s, self.ply=%s, moves=%s, board=%s" % \
            (repr(self.players), self.ply, moves, self.boards[-1]))
        log.debug("GameModel.undoMoves: acquiring self.applyingMoveLock\n")
        self.applyingMoveLock.acquire()
        log.debug("GameModel.undoMoves: self.applyingMoveLock acquired\n")
        try:
            self.emit("moves_undoing", moves)
            self.needsSave = True
            
            self.boards = self.variations[0]
            del self.boards[-moves:]
            del self.moves[-moves:]
            self.boards[-1].board.next = None
            
            for player in self.players:
                player.playerUndoMoves(moves, self)
            for spectator in self.spectators.values():
                spectator.spectatorUndoMoves(moves, self)
            
            log.debug("GameModel.undoMoves: undoing timemodel\n")
            if self.timemodel:
                self.timemodel.undoMoves(moves)
            
            self.checkStatus()
            self.setOpening()
        finally:
            log.debug("GameModel.undoMoves: releasing self.applyingMoveLock\n")
            self.applyingMoveLock.release()
        
        self.emit("moves_undone", moves)
    
    def isChanged (self):
        if self.ply == 0:
            return False
        if self.needsSave:
            return True
        if not self.uri or not isWriteable (self.uri):
            return True
        return False

    def add_variation(self, board, moves):
        board0 = board
        board = board0.clone()
        board.board.prev = None
        
        variation = [board]
        
        for move in moves:
            new = board.move(move)
            if len(variation) == 1:
                new.board.prev = board0.board
                variation[0].board.next = new.board
            else:
                new.board.prev = board.board
                board.board.next = new.board
            variation.append(new)
            board = new
        
        if board0.board.next is None:
            from pychess.Utils.lutils.LBoard import LBoard
            null_board = LBoard()
            null_board.prev = board0.board
            board0.board.next = null_board

        board0.board.next.children.append([board.board for board in variation])

        head = None
        for vari in self.variations:
            if board0 in vari:
                head = vari
                break
        
        self.variations.append(head[:board0.ply] + variation)
        self.needsSave = True
        self.emit("variations_changed")
