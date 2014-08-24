#from gobject import SIGNAL_RUN_FIRST
from gi.repository import GObject
from threading import Condition

from pychess.System.Log import log
from pychess.Players.Engine import Engine
from pychess.Utils.const import *
from pychess.Utils.repr import reprColor

class ProtocolEngine (Engine):
    
    __gsignals__ = {
        #"readyForOptions": (SIGNAL_RUN_FIRST, None, ()),
        #"readyForMoves": (SIGNAL_RUN_FIRST, None, ())
       "readyForOptions": (GObject.SIGNAL_RUN_FIRST, None, ()),
       "readyForMoves": (GObject.SIGNAL_RUN_FIRST, None, ())
    }
    
    #===========================================================================
    #    Setting engine options
    #===========================================================================
    
    def __init__ (self, subprocess, color, protover, md5):
        Engine.__init__(self, md5)
        
        self.engine = subprocess
        self.defname = subprocess.defname
        self.color = color
        self.protover = protover
        
        self.readyMoves = False
        self.readyOptions = False
        
        self.connected = True
        self.mode = NORMAL
        
        log.debug(reprColor[color], extra={"task":self.defname})
        
        self.movecon = Condition()
