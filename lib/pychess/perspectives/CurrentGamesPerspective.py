import os

import gtk

from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.System import prefix
from pychess.widgets.pydock.__init__ import CENTER, EAST, SOUTH

from pychess.panels.BoardPanel import BoardPanel
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.System import conf
from pychess.System.GtkWorker import GtkWorker
from pychess.Utils.const import *
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel 
from pychess.Variants import variants
from pychess.widgets.TaskerManager import TaskerManager
from pychess.widgets.TaskerManager import NewGameTasker
from pychess.widgets.TaskerManager import InternetGameTasker

from Perspective import Perspective

class CurrentGamesPerspective (Perspective):
    def __init__ (self):
        Perspective.__init__(self)
        self.setName(_("Current Games"))
        self.setDescription("...")
        self.setIconImage(gtk.image_new_from_stock("gtk-apply", gtk.ICON_SIZE_DND))
        
        tree = self.getBrowseTree()
        tree.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), text=0))
        model = gtk.ListStore(str)
        tree.set_model(model)
        #for i in xrange(5):
        #    model.append(["Thomas Dybdahl Ahle vs. GnuChess 4.1"])
        
        self.__games = []
        
        self.__notebooks = []
        self.__panels = []
        
        self.__dock = None
        
        self.addPanel(BoardPanel)
        
        self.__tasker = TaskerManager()
        self.__tasker.packTaskers (NewGameTasker(), InternetGameTasker())
        self.getWindow().add(self.__tasker)
        
        #self.games = {gmwidg: gamemodel}
    
    def addPanel (self, panel):
        """ panel: A class or function to call, to initialize new panels.
            A panel must be a widget, and is called with an instance of
            CurrentGamesPerspective and a GameModel. It must connect to the
            perspective in order to get information on?
            It must also check the game in order to see, if moves have already
            been made. """
        assert callable(panel)
        
        self.__panels.append(panel)
        if self.__dock:
            header, notebook = self.__createPanelHeaderAndBook(panel)
            self.__notebooks.append(notebook)
            for game in self.__games:
                notebook.append_page(panel(self, game))
            self.__dock.dock(notebook, EAST, header, panel.__title__)
    
    def addGame (self, gamemodel):
        if not self.__games:
            self.getWindow().remove(self.__tasker)
            if not self.__dock:
                self.__createAndInitDock()
            self.getWindow().add(self.__dock)
            self.__dock.show()
        
        self.__games.append(gamemodel)
        for notebook, panel in zip(self.__notebooks, self.__panels):
            notebook.append_page(panel(self, gamemodel))
            notebook.show_all()
            print notebook.get_children(), notebook.get_parent()
        
        gamename = "%s %s %s" % (gamemodel.players[0], _("vs."), gamemodel.players[1])
        self.getBrowseTree().get_model().append([gamename])
    
    def removeGame (self, gamemodel):
        gameno = self.__games.index(gamemodel)
        
        for notebook in self.__notebooks:
            notebook.remove_page(gameno)
        
        del self.__games[gameno]
        
        if not self.__games:
            self.getWindow().remove(self.__dock)
            self.getWindow().add(self.__tasker)
    
    def getToolbuttons(self):
        newgame = gtk.ToolButton(label="New Game")
        newgame.connect("clicked", self.__newGameClicked)
        return [newgame]
    
    def __newGameClicked(self, button):
        gamemodel = GameModel(TimeModel(5*60, 0))
        
        player0tup = (LOCAL, Human, (WHITE, ""), _("Human"))
        
        engine = discoverer.getEngineN(0)
        name = discoverer.getName(engine)
        player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                    (engine, BLACK, 8, variants[NORMALCHESS], 5*60, 0), name)
        
        self.createAndStartGame(gamemodel, player0tup, player1tup)
    
    def __createPanelHeaderAndBook (self, panel):
        """ Creates a HBox with an icon and a label and attaches a nice big
            tooltip """
        
        # Create panel notebook
        
        notebook = gtk.Notebook()
        notebook.props.show_tabs = False
        notebook.props.show_border = False
        
        # Create panel header
        
        hbox = gtk.HBox()
        label = gtk.Label(panel.__title__)
        label.set_size_request(0, 0)
        label.set_alignment(0, 1)
        if panel.__icon__:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(panel.__icon__, 16, 16)
        else:
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, 16, 16)
        icon = gtk.image_new_from_pixbuf(pixbuf)
        hbox.pack_start(icon, expand=False, fill=False)
        hbox.pack_start(label, expand=True, fill=True)
        hbox.set_spacing(2)
        hbox.show_all()
        
        if not hasattr(panel, "__dockable__") or not panel.__dockable__:
            tip = gtk.Tooltip()
            def cb (widget, x, y, keyboard_mode, tooltip, title, desc, filename):
                table = gtk.Table(2,2)
                table.set_row_spacings(2)
                table.set_col_spacings(6)
                table.set_border_width(4)
                if filename:
                    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, 56, 56)
                    image = gtk.image_new_from_pixbuf(pixbuf)
                    image.set_alignment(0, 0)
                    table.attach(image, 0,1,0,2)
                titleLabel = gtk.Label()
                titleLabel.set_markup("<b>%s</b>" % title)
                titleLabel.set_alignment(0, 0)
                table.attach(titleLabel, 1,2,0,1)
                descLabel = gtk.Label(desc)
                descLabel.props.wrap = True
                table.attach(descLabel, 1,2,1,2)
                tooltip.set_custom(table)
                table.show_all()
                return True
            hbox.props.has_tooltip = True
            hbox.connect("query-tooltip", cb, panel.__title__, panel.__desc__, panel.__icon__)
        
        return hbox, notebook
    
    def __createAndInitDock (self):
        self.__dock = PyDockTop("currentGames")
        
        dockLocation = prefix.addHomePrefix("pydock.xml")
        
        docks = {}
        for panel in self.__panels:
            header, notebook = self.__createPanelHeaderAndBook(panel)
            docks[panel.__title__] = (header, notebook)
            self.__notebooks.append(notebook)
        
        if os.path.isfile(dockLocation):
            try:
                dock.loadFromXML(dockLocation, docks)
            except Exception, e:
                #stringio = cStringIO.StringIO()
                #traceback.print_exc(file=stringio)
                #error = stringio.getvalue()
                #log.error("Dock loading error: %s\n%s" % (e, error))
                #md = gtk.MessageDialog(widgets["window1"], type=gtk.MESSAGE_ERROR,
                #                       buttons=gtk.BUTTONS_CLOSE)
                #md.set_markup(_("<b><big>PyChess was unable to load your panel settings</big></b>"))
                #md.format_secondary_text(_("Your panel settings have been reset. If this problem repeats, you should report it to the developers"))
                #md.run()
                #md.hide()
                os.remove(dockLocation)
                for header, panel in docks.values():
                    header.unparent()
                    panel.unparent()
        
        if not os.path.isfile(dockLocation):
            position = EAST
            leaf = self.__dock
            for panel, (header, notebook) in zip(self.__panels, docks.values()):
                leaf = leaf.dock(notebook, position, header, panel.__title__)
                header.show_all()
                if hasattr(panel, "__dockable__"):
                    leaf.setDockable(panel.__dockable__)
                position = EAST
        
        self.__dock.connect("unrealize", lambda dock: dock.saveToXML(dockLocation))
    
    #===========================================================================
    #    Creating and starting games
    #===========================================================================
    
    def createAndStartGame (self, gamemodel, player0tup, player1tup, loaddata=None):
        """ The player tuples are:
            (The type af player in a System.const value,
             A callable creating the player,
             A list of arguments for the callable,
             A preliminary name for the player)
            
            If loaddata is specified, it should be a tuple of:
            (A text uri or fileobj,
             A Savers.something module with a load function capable of loading it,
             An int of the game in file you want to load,
             The position from where to start the game) """
        
        worker = GtkWorker(self.__workfunc, gamemodel, player0tup, player1tup, loaddata)
        
        def onPublished (worker, vallist):
            for val in vallist:
                # The worker will start by publishing (gmwidg, game)
                if type(val) == tuple:
                    gmwidg, game = val
                    
                    #gamewidget.attachGameWidget(gmwidg)
                    #gamenanny.nurseGame(gmwidg, game)
                    #handler.emit("gmwidg_created", gmwidg, game)
                
                # Then the worker will publish functions setting up widget stuff
                elif callable(val):
                    val()
        worker.connect("published", onPublished)
        
        def onDone (worker, game):
            #gmwidg.connect("close_clicked", closeGame, game)
            self.addGame(game)
            worker.__del__()
        worker.connect("done", onDone)
        
        worker.execute()
    
    def __workfunc (self, worker, gamemodel, player0tup, player1tup, loaddata=None):
        #gmwidg = gamewidget.GameWidget(gamemodel)
        
        text = [name for t, f, a, name in (player0tup, player1tup)]
        text.insert(1,_("vs"))
        #gmwidg.setTabText(" ".join(text))
        
        worker.publish((None,gamemodel))
        
        # For updating names
        players = []
        def updateTitle (color=None):
            
            name0_name1 = gmwidg.getTabText().split(" %s "%_("vs"))
            if not name0_name1:
                name0, name1 = _("White"), _("Black")
            else: name0, name1 = name0_name1
            
            if color == None:
                name0 = repr(players[WHITE])
                name1 = repr(players[BLACK])
            elif color == WHITE:
                name0 = repr(players[WHITE])
            elif color == BLACK:
                name1 = repr(players[BLACK])
            
            gmwidg.setTabText("%s %s %s" % (name0, _("vs"), name1))
        
        # Initing players
        for i, playertup in enumerate((player0tup, player1tup)):
            type, func, args, name = playertup
            if type != LOCAL:
                players.append(func(*args))
                if type == ARTIFICIAL:
                    def readyformoves (player, color):
                        updateTitle(color)
                    #players[i].connect("readyForMoves", readyformoves, i)
            else:
                # Until PyChess has a proper profiles system, as discussed on the
                # issue tracker, we need to give human players special treatment
                player = func(None, *args)
                players.append(player)
                if i == 0 or (i == 1 and player0tup[0] != LOCAL):
                    key = "firstName"
                    alt = conf.username
                else:
                    key = "secondName"
                    alt = _("Guest")
                player.setName(conf.get(key, alt))
                
                def callback (none, color, key, alt):
                    players[color].setName(conf.get(key, alt))
                    #updateTitle(color)
                #conf.notify_add(key, callback, i, key, alt)
        
        #worker.publish(updateTitle)
        
        # Initing analyze engines
        anaengines = discoverer.getAnalyzers()
        specs = {}
        
        if conf.get("analyzer_check", True):
            engine = discoverer.getEngineByMd5(conf.get("ana_combobox", 0))
            if not engine: engine = anaengines[0]
            hintanalyzer = discoverer.initAnalyzerEngine(engine, ANALYZING,
                                                         gamemodel.variant)
            specs[HINT] = hintanalyzer
            #log.debug("Hint Analyzer: %s\n" % repr(hintanalyzer))
        
        if conf.get("inv_analyzer_check", True):
            engine = discoverer.getEngineByMd5(conf.get("inv_ana_combobox", 0))
            if not engine: engine = anaengines[0]
            spyanalyzer = discoverer.initAnalyzerEngine(engine, INVERSE_ANALYZING,
                                                        gamemodel.variant)
            specs[SPY] = spyanalyzer
            #log.debug("Spy Analyzer: %s\n" % repr(spyanalyzer))
        
        # Setting game
        gamemodel.setPlayers(players)
        gamemodel.setSpectactors(specs)
        
        # Starting
        if loaddata:
            try:
                uri, loader, gameno, position = loaddata
                gamemodel.loadAndStart (uri, loader, gameno, position)
            except LoadingError, e:
                d = gtk.MessageDialog (type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_OK)
                d.set_markup ("<big><b>%s</b></big>" % e.args[0])
                d.format_secondary_text (e.args[1] + "\n\n" +
                        _("Correct the move, or start playing with what could be read"))
                d.connect("response", lambda d,a: d.hide())
                worker.publish(d.show)
        
        else:
            if gamemodel.variant.need_initial_board:
                for player in gamemodel.players + gamemodel.spectactors.values():
                    player.setOptionInitialBoard(gamemodel)
            
            gamemodel.start()
        
        return gamemodel
    
    #===========================================================================
    #    Loading
    #===========================================================================
    
    opendialog = None
    savedialog = None
    enddir = {}
    def getOpenAndSaveDialogs():
        global opendialog, savedialog, enddir, savecombo, savers
        
        if not opendialog:
            types = []
            savers = [getattr(Savers, s) for s in Savers.__all__]
            for saver in savers:
                for ending in saver.__endings__:
                    enddir[ending] = saver
                    types.append((saver.__label__, saver.__endings__))
            
            opendialog = gtk.FileChooserDialog(_("Open Game"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
            savedialog = gtk.FileChooserDialog(_("Save Game"), None, gtk.FILE_CHOOSER_ACTION_SAVE,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
            savedialog.set_current_folder(os.environ["HOME"])
            saveformats = gtk.ListStore(str, str)
            
            # All files filter
            star = gtk.FileFilter()
            star.set_name(_("All Files"))
            star.add_pattern("*")
            opendialog.add_filter(star)
            saveformats.append([_("Detect type automatically"), ""])
            
            # All chess files filter
            all = gtk.FileFilter()
            all.set_name(_("All Chess Files"))
            opendialog.add_filter(all)
            opendialog.set_filter(all)
            
            # Specific filters and save formats
            default = 0
            for i, (label, endings) in enumerate(types):
                endstr = "(%s)" % ", ".join(endings)
                f = gtk.FileFilter()
                f.set_name(label+" "+endstr)
                for ending in endings:
                    f.add_pattern("*."+ending)
                    all.add_pattern("*."+ending)
                opendialog.add_filter(f)
                saveformats.append([label, endstr])
                if "pgn" in endstr:
                    default = i + 1
            
            # Add widgets to the savedialog
            savecombo = gtk.ComboBox()
            savecombo.set_model(saveformats)
            crt = gtk.CellRendererText()
            savecombo.pack_start(crt, True)
            savecombo.add_attribute(crt, 'text', 0)
            crt = gtk.CellRendererText()
            savecombo.pack_start(crt, False)
            savecombo.add_attribute(crt, 'text', 1)
            savecombo.set_active(default)
            savedialog.set_extra_widget(savecombo)
        
        return opendialog, savedialog, enddir, savecombo, savers
    
    #===========================================================================
    #    Saving
    #===========================================================================
    
    def saveGame (game):
        if not game.isChanged():
            return
        if game.uri and isWriteable (game.uri):
            saveGameSimple (game.uri, game)
        else:
            return saveGameAs (game)
    
    def saveGameSimple (uri, game):
        ending = os.path.splitext(uri)[1]
        if not ending: return
        saver = enddir[ending[1:]]
        game.save(uri, saver, append=False)
    
    def saveGameAs (game):
        opendialog, savedialog, enddir, savecombo, savers = getOpenAndSaveDialogs()
        
        # Keep running the dialog until the user has canceled it or made an error
        # free operation
        while True:
            savedialog.set_current_name("%s %s %s" %
                                       (game.players[0], _("vs."), game.players[1]))
            res = savedialog.run()
            if res != gtk.RESPONSE_ACCEPT:
                break
            
            uri = savedialog.get_filename()
            ending = os.path.splitext(uri)[1]
            if ending.startswith("."): ending = ending[1:]
            
            append = False
            
            if savecombo.get_active() == 0:
                if not ending in enddir:
                    d = gtk.MessageDialog(
                            type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
                    folder, file = os.path.split(uri)
                    d.set_markup(
                              _("<big><b>Unknown file type '%s'</b></big>") % ending)
                    d.format_secondary_text(_("Was unable to save '%s' as PyChess doesn't know the format '%s'.") % (uri,ending))
                    d.run()
                    d.hide()
                    continue
                else:
                    saver = enddir[ending]
            else:
                saver = savers[savecombo.get_active()-1]
                if not ending in enddir or not saver == enddir[ending]:
                    uri += ".%s" % saver.__endings__[0]
            
            if os.path.isfile(uri) and not os.access (uri, os.W_OK):
                d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
                d.set_markup(_("<big><b>Unable to save file '%s'</b></big>") % uri)
                d.format_secondary_text(
                    _("You don't have the necessary rights to save the file.\n\
    Please ensure that you have given the right path and try again."))
                d.run()
                d.hide()
                continue
            
            if os.path.isfile(uri):
                d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
                d.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, _("_Replace"),
                            gtk.RESPONSE_ACCEPT)
                if saver.__append__:
                    d.add_buttons(gtk.STOCK_ADD, 1)
                d.set_title(_("File exists"))
                folder, file = os.path.split(uri)
                d.set_markup(_("<big><b>A file named '%s' already exists. Would you like to replace it?</b></big>") % file)
                d.format_secondary_text(_("The file already exists in '%s'. If you replace it, its content will be overwritten.") % folder)
                replaceRes = d.run()
                d.hide()
                
                if replaceRes == 1:
                    append = True
                elif replaceRes == gtk.RESPONSE_CANCEL:
                    continue
            else:
                print repr(uri)
            try:
                game.save(uri, saver, append)
            except IOError, e:
                d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR)
                d.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
                d.set_title(_("Could not save the file"))
                d.set_markup(_("<big><b>PyChess was not able to save the game</b></big>"))
                d.format_secondary_text(_("The error was: %s") % ", ".join(str(a) for a in e.args))
                os.remove(uri)
                d.run()
                d.hide()
                continue
            
            break
        
        savedialog.hide()
        return res
    
    #===========================================================================
    #    Closing
    #===========================================================================
    
    def closeAllGames (pairs):
        changedPairs = [(gmwidg, game) for gmwidg, game in pairs if game.isChanged()]
        if len(changedPairs) == 0:
            response = gtk.RESPONSE_OK
        elif len(changedPairs) == 1:
            response = closeGame(*changedPairs[0])
        else:
            widgets = GladeWidgets("saveGamesDialog.glade")
            dialog = widgets["saveGamesDialog"]
            heading = widgets["saveGamesDialogHeading"]
            saveLabel = widgets["saveGamesDialogSaveLabel"]
            treeview = widgets["saveGamesDialogTreeview"]
            
            heading.set_markup("<big><b>" +
                               _n("There are %d game with unsaved moves.",
                                  "There are %d games with unsaved moves.",
                                  len(changedPairs)) % len(changedPairs) +
                               " " + _("Save moves before closing?") +
                               "</b></big>")
            
            liststore = gtk.ListStore(bool, str)
            treeview.set_model(liststore)
            renderer = gtk.CellRendererToggle()
            renderer.props.activatable = True
            treeview.append_column(gtk.TreeViewColumn("", renderer, active=0))
            treeview.append_column(gtk.TreeViewColumn("", gtk.CellRendererText(), text=1))
            for gmwidg, game in changedPairs:
                liststore.append((True, "%s %s %s" %
                                 (game.players[0], _("vs."), game.players[1])))
            
            def callback (cell, path):
                if path:
                    liststore[path][0] = not liststore[path][0]
                saves = len(tuple(row for row in liststore if row[0]))
                saveLabel.set_text(_n("_Save %d document", "_Save %d documents", saves) % saves)
                saveLabel.set_use_underline(True)
            renderer.connect("toggled", callback)
            
            callback(None, None)
            
            while True:
                response = dialog.run()
                if response == gtk.RESPONSE_YES:
                    for i in xrange(len(liststore)-1, -1, -1):
                        checked, name = liststore[i]
                        if checked:
                            gmwidg, game = changedPairs[i]
                            if saveGame(game) == gtk.RESPONSE_ACCEPT:
                                del pairs[i]
                                liststore.remove(liststore.get_iter((i,)))
                                game.end(ABORTED, ABORTED_AGREEMENT)
                                gamewidget.delGameWidget(gmwidg)
                            else:
                                break
                    else:
                        break
                else:
                    break
            dialog.destroy()
        
        if response not in (gtk.RESPONSE_DELETE_EVENT, gtk.RESPONSE_CANCEL):
            for gmwidg, game in pairs:
                game.end(ABORTED, ABORTED_AGREEMENT)
                game.terminate()
        
        return response
    
    def closeGame (gmwidg, game):
        if not game.isChanged():
            response = gtk.RESPONSE_OK
        else:
            d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
            d.add_button(_("Close _without Saving"), gtk.RESPONSE_OK)
            d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            if game.uri:
                d.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_YES)
            else: d.add_button(gtk.STOCK_SAVE_AS, gtk.RESPONSE_YES)
            
            gmwidg.bringToFront()
            
            d.set_markup(_("<b><big>Save the current game before you close it?</big></b>"))
            d.format_secondary_text (_(
                "It is not possible later to continue the game,\nif you don't save it."))
            response = d.run()
            d.destroy()
            
            if response == gtk.RESPONSE_YES:
                # Test if cancel was pressed in the save-file-dialog
                if saveGame(game) != gtk.RESPONSE_ACCEPT:
                    response = gtk.RESPONSE_CANCEL
        
        if response not in (gtk.RESPONSE_DELETE_EVENT, gtk.RESPONSE_CANCEL):
            if game.status in UNFINISHED_STATES:
                game.end(ABORTED, ABORTED_AGREEMENT)
            game.terminate()
            gamewidget.delGameWidget (gmwidg)
        
        return response
    
################################################################################
# gameDic - containing the gamewidget:gamemodel of all open games              #
################################################################################
gameDic = {}
chessFiles = {}

class GladeHandlers:
    
    def on_gmwidg_created (handler, gmwidg, gamemodel):
        gameDic[gmwidg] = gamemodel
        
        # Bring playing window to the front
        gamewidget.getWidgets()["window1"].present()
        
        # Make sure game dependent menu entries are sensitive
        for widget in gamewidget.MENU_ITEMS:
            gamewidget.getWidgets()[widget].set_property('sensitive', True)
        
        # Make sure we can remove gamewidgets from gameDic later
        gmwidg.connect("closed", GladeHandlers.__dict__["on_gmwidg_closed"])
    
    def on_gmwidg_closed (gmwidg):
        del gameDic[gmwidg]
        if not gameDic:
            for widget in gamewidget.MENU_ITEMS:
                gamewidget.getWidgets()[widget].set_property('sensitive', False)
    
    #          Drag 'n' Drop          #
    
    def on_drag_received (wi, context, x, y, selection, target_type, timestamp):
        uri = selection.data.strip()
        uris = uri.split()
        if len(uris) > 1:
            log.warn("%d files were dropped. Only loading the first" % len(uris))
        uri = uris[0]
        newGameDialog.LoadFileExtension.run(uri)
    
    #          Game Menu          #
    
    def on_new_game1_activate (widget):
        newGameDialog.NewGameMode.run()
    
    def on_play_internet_chess_activate (widget):
        ICLogon.run()
    
    def on_load_game1_activate (widget):
        newGameDialog.LoadFileExtension.run(None, chessFiles)
    
    def on_set_up_position_activate (widget):
        # Not implemented
        pass
    
    def on_enter_game_notation_activate (widget):
        newGameDialog.EnterNotationExtension.run()
    
    def on_save_game1_activate (widget):
        ionest.saveGame (gameDic[gamewidget.cur_gmwidg()])
    
    def on_save_game_as1_activate (widget):
        ionest.saveGameAs (gameDic[gamewidget.cur_gmwidg()])
    
    def on_properties1_activate (widget):
        gameinfoDialog.run(gamewidget.getWidgets(), gameDic)
    
    def on_player_rating1_activate (widget):
        playerinfoDialog.run(gamewidget.getWidgets())
    
    def on_close1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        response = ionest.closeGame(gmwidg, gameDic[gmwidg])
    
    def on_quit1_activate (widget, *args):
        if ionest.closeAllGames(gameDic.items()) in (gtk.RESPONSE_OK, gtk.RESPONSE_YES):
            gtk.main_quit()
        else: return True
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        if gmwidg.board.view.rotation:
            gmwidg.board.view.rotation = 0
        else:
            gmwidg.board.view.rotation = math.pi

    
    def on_fullscreen1_activate (widget):
        gamewidget.getWidgets()["window1"].fullscreen()
        gamewidget.getWidgets()["fullscreen1"].hide()
        gamewidget.getWidgets()["leave_fullscreen1"].show()
    
    def on_leave_fullscreen1_activate (widget):
        gamewidget.getWidgets()["window1"].unfullscreen()
        gamewidget.getWidgets()["leave_fullscreen1"].hide()
        gamewidget.getWidgets()["fullscreen1"].show()
    
    def on_about1_activate (widget):
        gamewidget.getWidgets()["aboutdialog1"].show()
    
    def on_log_viewer1_activate (widget):
        if widget.get_active():
            LogDialog.show()
        else: LogDialog.hide()
    
    def on_show_sidepanels_activate (widget):
        gamewidget.zoomToBoard(not widget.get_active())
    
    def on_hint_mode_activate (widget):
        for gmwidg in gameDic.keys():
            gamenanny.setAnalyzerEnabled(gmwidg, HINT, widget.get_active())
    
    def on_spy_mode_activate (widget):
        for gmwidg in gameDic.keys():
            print "setting spymode for", gmwidg, "to", widget.get_active()
            gamenanny.setAnalyzerEnabled(gmwidg, SPY, widget.get_active())
    
    #          Settings menu          #
    
    def on_preferences_activate (widget):
        preferencesDialog.run(gamewidget.getWidgets())
    
    #          Help menu          #
    
    def on_about_chess1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))
    
    def on_how_to_play1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))

    def translate_this_application_activate(widget):
        webbrowser.open("http://code.google.com/p/pychess/wiki/RosettaTranslates")
        
    def on_TipOfTheDayMenuItem_activate (widget):
        tipOfTheDay.TipOfTheDay.show()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        gamewidget.getWidgets()["notebook3"].set_current_page(page_num)
    