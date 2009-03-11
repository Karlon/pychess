import gtk
import gobject

class Perspective (gobject.GObject):
    
    __gsignals__ = {
        "pending":  (gobject.SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__(self):
        self.__name = ""
        self.__description = ""
        self.__iconImage = None
        self.__browseTree = gtk.TreeView()
        self.__window = gtk.Alignment(0,0,1,1)
        
        self.__browseTree.props.headers_visible = False
    
    
    def show (self):
        pass
    
    def hide (self):
        pass
    
    
    def getName(self):
        return self.__name

    def getDescription(self):
        return self.__description

    def getIconImage(self):
        return self.__iconImage
    
    
    def setName(self, name):
        self.__name = name

    def setDescription(self, description):
        self.__description = description

    def setIconImage(self, iconImage):
        self.__iconImage = iconImage
    
    
    def getBrowseTree (self):
        return self.__browseTree
    
    def getWindow(self):
        return self.__window
    
    def getToolbuttons(self):
        return []
