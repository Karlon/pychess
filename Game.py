import os, thread
import datetime
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from Utils.History import History
import Utils.Move
from Utils.eval import evaluateComplete
#from Utils.book import getBestOpening, getOpenings

from Players.Engine import EngineDead
from Utils.validator import FINE, DRAW, WHITEWON, BLACKWON
from Utils.validator import DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, WON_RESIGN, WON_CALLFLAG, WON_MATE

from statusbar import status

profile = False

class Game (GObject):

    __gsignals__ = {
        'game_ended' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,int))
    }

    def __init__(self, his, oracle, p1, p2, cc = None, seconds = 0, plus = 0):
        GObject.__init__(self)
    
        self.player1 = p1
        self.player2 = p2
        self.chessclock = cc
        self.history = his
        self.event = 'Local Event'
        self.site = 'Local site'
        self.round = '1'
        today = datetime.date.today()
        self.year = str(today.year)
        self.month = str(today.month)
        if len(self.month) == 1:
            self.month = "0" + self.month
        self.day = str(today.day)
        if len(self.day) == 1:
            self.day = "0" + self.day
        
        if self.chessclock:
            self.chessclock.setTime(seconds*10)
            self.chessclock.setGain(plus*10)
        
        self.history.connect("game_ended", lambda h,stat,comm: self.emit("game_ended", stat, comm))
        
        self.player1.connect("action", self._action)
        self.player2.connect("action", self._action)
    
    def run (self):
        self.connect_after("game_ended", lambda g,stat,comm: self.kill())
        if not profile:
            thread.start_new(self._run, ())
        else:
            def do():
                from profile import runctx
                loc = locals()
                loc["self"] = self
                runctx ("self._run()", loc, globals(), "/tmp/pychessprofile")
                from pstats import Stats
                s = Stats("/tmp/pychessprofile")
                s.sort_stats("time")
                s.print_stats()
            thread.start_new(do,())
    
    def _run (self):
        self.run = True
        while self.run:
            player = {"white":self.player1, "black":self.player2}[self.history.curCol()]
            try:
                answer = player.makeMove(self.history)
            
            except Utils.Move.ParsingError:
                #Mostly debugging really
                import traceback
                print traceback.format_exc()
                print "Player 1 board:"
                self.player1.showBoard()
                print "Player 2 board:"
                self.player2.showBoard()
                import sys
                sys.exit()
                
            except EngineDead:
                self.run = False
                break
                
            if type(answer) in (list, tuple):
                move, animate = answer
            else: move, animate = answer, True
            
            if not self.run:
                log.warn("The 'line' in Game.py was used :O")
                break
            
            if not self.history.add(move,True):
                self.kill()
                break
            
            #print getOpenings(self.history)
            #print getBestOpening(self.history)
            #print "ADDED MOVE %s, SCORE IS NOW: %d" % (move.algNotat(self.history), evaluateComplete(self.history))
            
            if self.chessclock:
                self.chessclock.switch()
                
    def kill (self):
        self.run = False
        if self.player1: self.player1.__del__()
        if self.player2: self.player2.__del__()
        if self.chessclock: self.chessclock.stop()
    
    def _action (self, player, action):

        if action == player.RESIGNATION:
            p = player == self.player2 and WHITEWON or BLACKWON
            self.emit("game_ended", p, WON_RESIGN)
            
        elif action == player.DRAW_OFFER:
            status(_("Draw offer has been sent"), True)
            otherPlayer = player == self.player1 and self.player2 or self.player1
            otherPlayer.offerDraw()
            
        elif action == player.DRAW_ACCEPTION:
            #FIXME: Test if draw is (still) valid
            self.emit("game_ended", DRAW, DRAW_AGREE)
            
        elif action == player.FLAG_CALL:
            if not self.chessclock:
                status(_("Couldn't call flag in game with no timecontrols"), True)
                return
            p = player == self.player2 and BLACKWON or WHITEWON
            p_other = player == self.player1 and 1 or 0
            if self.chessclock._get_playerTime(p_other) <= 0:
                self.emit("game_ended", p, WON_CALLFLAG)
            else:
                status(_("Couldn't call flag on player not out of time"), True)
                
    def _get_active_player (self):
        return self.history.curCol() == "white" and self.player1 or self.player2
    activePlayer = property(_get_active_player)
