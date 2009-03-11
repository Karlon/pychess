import sys
import webbrowser
import math
import atexit
import signal

import pango, gobject, gtk
from gtk import DEST_DEFAULT_MOTION, DEST_DEFAULT_HIGHLIGHT, DEST_DEFAULT_DROP

from pychess.System import conf, glock, uistuff
from pychess.System.uistuff import POSITION_NONE, POSITION_CENTER, POSITION_GOLDEN
from pychess.System.Log import log
from pychess.Utils.const import *
from pychess.Utils import book # Kills pychess if no sqlite available
from pychess.widgets import newGameDialog
from pychess.widgets import tipOfTheDay
from pychess.widgets import LogDialog
from pychess.widgets.discovererDialog import DiscovererDialog
from pychess.widgets import gamewidget
from pychess.widgets import gamenanny
from pychess.widgets import ionest
from pychess.widgets import preferencesDialog, gameinfoDialog, playerinfoDialog

from pychess.Players.engineNest import discoverer
from pychess.ic import ICLogon

################################################################################
# gameDic - containing the gamewidget:gamemodel of all open games              #
################################################################################
gameDic = {}
chessFiles = {}

dnd_list = [ ('application/x-chess-pgn', 0, 0xbadbeef),
             ('application/da-chess-pgn', 0, 0x7cf*0x17ee1),
             ('text/plain', 0, 0xbadbeef) ]

minimumMenu = """
    <ui>
        <menubar name='Menubar'>
            <menu action='FileMenu'>
                <menuitem action='New'/>
                <menuitem action='Open'/>
                <separator/>
                <menuitem action='Close'/>
                <menuitem action='Quit'/>
            </menu>
            <menu action='HelpMenu'>
                <menuitem action='About'/>
            </menu>
        </menubar>
    </ui>
"""

from pychess.perspectives.CurrentGamesPerspective import *
from pychess.perspectives.UsersAndEnginesPerspective import *
from pychess.widgets.Background import giveBackground

class Main (gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        
        self.__perspectives = []
        
        self.__createMinimumUI()
        
        mainVBox = gtk.VBox()
        mainHBox = gtk.HBox()
        rightVBox = gtk.VBox()
        self.__toolbar = gtk.Toolbar()
        self.__perspectivesNotebook = gtk.Notebook()
        self.__perspectivesNotebook.props.show_tabs = False
        self.__perspectivesNotebook.props.show_border = False
        self.__perspectiveVBox = gtk.VBox()
        self.__perspectiveVBox.set_size_request(300, -1)
        self.__perspectiveVBox.props.border_width = 2
        self.__perspectiveVBox.props.spacing = 2
        
        #giveBackground(self.__perspectiveVBox)
        #import gobject
        #gobject.idle_add(lambda: giveBackground(mainVBox))
        
        mainVBox.pack_start(self.__ui.get_widget("/Menubar"), False, True)
        mainVBox.pack_start(mainHBox, True, True)
        mainHBox.pack_start(self.__perspectiveVBox, False, True)
        mainHBox.pack_start(rightVBox, True, True)
        rightVBox.pack_start(self.__toolbar, False, True)
        rightVBox.pack_start(self.__perspectivesNotebook, True, True)
        
        self.add(mainVBox)
    
    def addPerspective (self, perspective):
        assert perspective.getIconImage().get_storage_type() not in \
            (gtk.IMAGE_PIXMAP, gtk.IMAGE_IMAGE, gtk.IMAGE_ANIMATION)
        
        button = gtk.ToggleButton()
        button.props.active = False
        hbox = gtk.HBox()
        image = perspective.getIconImage()
        image.set_padding(8, 0)
        hbox.pack_start(image, False, True)
        label = gtk.Label()
        label.props.xalign = 0
        label.set_markup("<big>%s</big>" % perspective.getName())
        hbox.pack_start(label, True, True)
        #hbox.pack_start(perspective.getPendingLabel())
        button.add(hbox)
        button.show_all()
        
        sw = gtk.ScrolledWindow()
        sw.props.shadow_type = gtk.SHADOW_IN
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(perspective.getBrowseTree())
        sw.hide()
        
        self.__perspectiveVBox.pack_start(button, False, True)
        self.__perspectiveVBox.pack_start(sw, True, True)
        self.__perspectivesNotebook.append_page(perspective.getWindow())
        self.__perspectivesNotebook.show_all()
        for toolbutton in perspective.getToolbuttons():
            self.__toolbar.add(toolbutton)
            toolbutton.show()
        
        # Convert from gtk.Image to stockicon
        iconname = None
        if image.get_storage_type() != gtk.IMAGE_EMPTY:
            if image.get_storage_type() == gtk.IMAGE_STOCK:
                iconname, iconsize = perspective.getIconImage().get_stock()
            else:
                iconname = perspective.getName()
                if image.get_storage_type() == gtk.IMAGE_PIXBUF:
                    pixbuf = image.get_pixbuf()
                elif image.get_storage_type() == gtk.IMAGE_ICON_SET:
                    pixbuf = image.get_icon_set().render_icon(style, direction, state, size, widget, detail)
                iconsource = gtk.IconSource()
                iconsource.set_pixbuf(pixbuf)
                iconset = gtk.IconSet()
                iconset.add_source(iconsource)
                iconfactory = gtk.IconFactory()
                iconfactory.add(iconname, iconset)
                iconfactory.add_default() 
        
        # Add item to Perspective menu
        ag = gtk.ActionGroup('PerspectiveActions')
        action = gtk.Action(perspective.getName(), perspective.getName(),
                            perspective.getDescription(), iconname)
        action.connect("activate", lambda a, p: self.showPerspective(p), perspective)
        ag.add_action_with_accel(action, '<control>%d' % (len(self.__perspectives)+1))
        ag.add_action(gtk.Action('Perspectives', '_Perspectives', None, None))
        self.__ui.insert_action_group(ag, 0)
        uistring = "<ui><menubar name='Menubar'><menu action='Perspectives'>" +\
                   "<menuitem action='%s'/></menu></menubar></ui>" % perspective.getName()
        self.__ui.add_ui_from_string(uistring)
        
        # ...
        self.__perspectives.append((perspective, button))
        button.connect("clicked", self.__onPerspectiveButtonClicked)
    
    def removePerspective (self, perspective):
        """ This is used only if hiding/showing of perspectives are implemented """
        perspective.hide()
        button = [b for p, b in self.__perspectives if p == perspective][0]
        self.__perspectiveVBox.remove(button)
        self.__perspectiveVBox.remove(perspective.getBrowseTree())
        for ag in get_action_groups():
            if ag.get_name() == 'PerspectiveActions':
                pass
                #TODO: Update accels
    
    def showPerspective (self, perspective):
        for num, (iperspective, button) in enumerate(self.__perspectives):
            button.handler_block_by_func(self.__onPerspectiveButtonClicked)
            if iperspective is perspective:
                button.props.active = True
                iperspective.show()
                iperspective.getBrowseTree().get_parent().show_all()
                self.__perspectivesNotebook.set_current_page(num)
            else:
                button.props.active = False
                iperspective.hide()
                iperspective.getBrowseTree().get_parent().hide()
            button.handler_unblock_by_func(self.__onPerspectiveButtonClicked)
    
    def getPerspectives (self):
        return (perspective for (perspective, button) in self.__perspectives)
    
    def __onPerspectiveButtonClicked (self, sourceButton):
        for perspective, button in self.__perspectives:
            if button == sourceButton:
                self.showPerspective(perspective)
                break
    
    def __createMinimumUI (self):
        ag = gtk.ActionGroup('WindowActions')
        ag.add_actions([
            ('FileMenu', None, '_File'),
                ('New', gtk.STOCK_NEW, '_New', '<control>N',
                 'Create a new file', lambda *a: None),
                ('Open', gtk.STOCK_OPEN, '_Open', '<control>O',
                 'Open a file', lambda *a: None),
                ('Close', gtk.STOCK_CLOSE, '_Close', '<control>W',
                 'Close the current window', lambda *a: None),
                ('Quit', gtk.STOCK_QUIT, '_Quit', '<control>Q',
                 'Quit application', lambda *a: None),
            ('HelpMenu', None, '_Help'),
                ('About',    None, '_About', None,
                 'About application', lambda *a: None),
            ])
        self.__ui = gtk.UIManager()
        self.__ui.insert_action_group(ag, 0)
        self.__ui.add_ui_from_string(minimumMenu)
        self.add_accel_group(self.__ui.get_accel_group())
    
    def bringItOn (self):
        self.show_all()
        self.showPerspective(self.getPerspectives().next())

def run (args):
    
    main = Main()
    uistuff.keepWindowSize("main", main, (575,479), POSITION_GOLDEN)
    main.addPerspective(CurrentGamesPerspective())
    main.addPerspective(UsersAndEnginesPerspective())
    main.connect("delete-event", gtk.main_quit)
    
    def discovering_started (discoverer, binnames):
        DiscovererDialog.show(discoverer, binnames, parent=main)
    glock.glock_connect(discoverer, "discovering_started", discovering_started)
    gobject.idle_add(discoverer.start)
    
    plugins = PluginEngine()
    plugins.registerPlugins(main)
    
    main.bringItOn()
    gtk.gdk.threads_init()
    gtk.main()



from pychess.System import prefix
import os.path
import imp
from Plugin import Plugin

class PluginEngine (gobject.GObject):
    
    __gsignals__ = {
        "plugin_added":  (gobject.SIGNAL_RUN_FIRST, None, (object, object)),
        "plugin_removed":  (gobject.SIGNAL_RUN_FIRST, None, ()),
        "plugin_toggled": (gobject.SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self):
        gobject.GObject.__init__(self)
        self.__plugins = []
    
    def registerPlugins (self, main):
        plugins = []
        for root in (prefix.getDataPrefix(), prefix.getHomePrefix()):
            if "plugins" in os.listdir(root):
                path = os.path.join(root, "plugins")
                if os.path.isdir(path):
                    for file in os.listdir(path):
                        if file.endswith(".pychess-plugin"):
                            infofile = os.path.join(path, file)
                            module = imp.find_module(file[:-15], [path])
                            # Validation could go here
                            plugins.append((infofile, module))
        
        oldsubclasses = set()
        for infofile, module in plugins:
            imp.load_module("__init__.py", *module)
            subclasses = set(Plugin.__subclasses__())
            pluginclass, = subclasses.difference(oldsubclasses)
            oldsubclasses = subclasses
            
            plugin = pluginclass()
            plugin.activate(main)
            dic = self.__parseInfofile(open(infofile))
            self.emit("plugin_added", plugin, dic)
    
    def __parseInfofile (self, file):
        dic = {"iage": 1,
               "name": "No Name",
               "description": "No Description",
               "authors": "",
               "copyright": "",
               "website": ""}
        
        for line in file:
            line = line.strip()
            if "=" not in line: continue
            key, value = line.split("=", 1)
            dic[key.lower()] = value
        
        return dic
    
    def installPlugin (self, path):
        pass

class PyChess:
    def __init__(self, args):
        self.initGlade()
        self.handleArgs(args)
    
    def initGlade(self):
        #=======================================================================
        # Init glade and the 'GladeHandlers'
        #=======================================================================
        gtk.glade.set_custom_handler(self.widgetHandler)
        widgets = uistuff.GladeWidgets("PyChess.glade")
        widgets.getGlade().signal_autoconnect(GladeHandlers.__dict__)
        
        #------------------------------------------------------ Redirect widgets
        gamewidget.setWidgets(widgets)
        
        #-------------------------- Main.py still needs a minimum of information
        ionest.handler.connect("gmwidg_created",
                               GladeHandlers.__dict__["on_gmwidg_created"])
        
        #---------------------- The only two menuitems that need special initing
        uistuff.keep(widgets["hint_mode"], "hint_mode")
        uistuff.keep(widgets["spy_mode"], "spy_mode")
        
        #=======================================================================
        # Show main window and init d'n'd
        #=======================================================================
        uistuff.keepWindowSize("main", widgets["window1"], (575,479), POSITION_GOLDEN)
        widgets["window1"].show()
        widgets["Background"].show_all()
        
        flags = DEST_DEFAULT_MOTION | DEST_DEFAULT_HIGHLIGHT | DEST_DEFAULT_DROP
        widgets["menubar1"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        widgets["Background"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        
        #=======================================================================
        # Init 'minor' dialogs
        #=======================================================================
        
        #------------------------------------------------------------ Log dialog
        LogDialog.add_destroy_notify(lambda: widgets["log_viewer1"].set_active(0))
        
        #---------------------------------------------------------- About dialog
        clb = widgets["aboutdialog1"].get_child().get_children()[1].get_children()[2]
        widgets["aboutdialog1"].set_name(NAME)
        widgets["aboutdialog1"].set_version(VERSION_NAME+" "+VERSION)
        def callback(button, *args):
            widgets["aboutdialog1"].hide()
            return True
        clb.connect("activate", callback)
        clb.connect("clicked", callback)
        widgets["aboutdialog1"].connect("delete-event", callback)
        
        #----------------------------------------------------- Discoverer dialog
        def discovering_started (discoverer, binnames):
            DiscovererDialog.show(discoverer, binnames, widgets["window1"])
        glock.glock_connect(discoverer, "discovering_started", discovering_started)
        gobject.idle_add(discoverer.start)
        
        #------------------------------------------------- Tip of the day dialog
        if conf.get("show_tip_at_startup", False):
            tipOfTheDay.TipOfTheDay.show()
    
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        # Tasker is currently the only widget that uses glades CustomWidget
        tasker = TaskerManager()
        tasker.packTaskers (NewGameTasker(), InternetGameTasker())
        return tasker
    
    def handleArgs (self, args):
        if args:
            def do (discoverer):
                newGameDialog.LoadFileExtension.run(args[0], chessFiles)
            glock.glock_connect_after(discoverer, "all_engines_discovered", do)

def run2 (args):
    import gtkexcepthook
    PyChess(args)
    signal.signal(signal.SIGINT, gtk.main_quit)
    gtk.gdk.threads_init()
    gtk.main()
