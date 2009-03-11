import gtk

from pychess.widgets.BoardControl import BoardControl
from pychess.System.prefix import addDataPrefix

class BoardPanel (gtk.Table):
    
    __title__ = "Board Panel"
    __dockable__ = False
    __icon__ = None
    __desc__ = ""
    
    def __init__ (self, currentGamesPerspective, gamemodel):
        gtk.Table.__init__(self)
        
        self.__currentGamesPerspective = currentGamesPerspective
        self.__gamemodel = gamemodel
        
        boardControl = BoardControl(gamemodel, {})
        self.add(boardControl)
