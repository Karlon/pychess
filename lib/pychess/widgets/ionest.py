""" The task of this module, is to save, load and init new games """

from gi.repository import GObject

from pychess import Savers
from pychess.Savers.ChessFile import LoadingError
from pychess.Savers import * # This needs an import all not to break autoloading
from pychess.System import conf
from pychess.System.GtkWorker import GtkWorker
from pychess.System.Log import log
from pychess.System.protoopen import isWriteable
from pychess.System.uistuff import GladeWidgets, keep
from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.widgets import gamenanny, gamewidget
from gi.repository import Gtk
import os


def generalStart (gamemodel, player0tup, player1tup, loaddata=None):
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
    log.debug("ionest.generalStart: %s\n %s\n %s" % (gamemodel, player0tup, player1tup))

    def work (w): 
        return workfunc(w, gamemodel, player0tup, player1tup, loaddata)
    worker = GtkWorker(work)

    def onPublished (worker, vallist):
        for val in vallist:
            # The worker will start by publishing (gmwidg, game)
            if type(val) == tuple:
                gmwidg, game = val
                gamewidget.attachGameWidget(gmwidg)
                gamenanny.nurseGame(gmwidg, game)
                log.debug("onPublished: -> emit gmwidg_created: %s" % (gmwidg))
                handler.emit("gmwidg_created", gmwidg, game)
                log.debug("onPublished: <- emit gmwidg_created: %s" % (gmwidg))

            # Then the worker will publish functions setting up widget stuff
            elif callable(val):
                val()
    worker.connect("published", onPublished)

    def onDone (worker, (gmwidg, game)):
        gmwidg.connect("close_clicked", closeGame, game)
        worker._del()
    worker.connect("done", onDone)

    worker.execute()

def workfunc (worker, gamemodel, player0tup, player1tup, loaddata=None):
    log.debug("ionest.workfunc: %s\n %s\n %s" % (gamemodel, player0tup, player1tup))

    gmwidg = gamewidget.GameWidget(gamemodel)
    worker.publish((gmwidg,gamemodel))
    
    # Initing players
    players = []
    for i, playertup in enumerate((player0tup, player1tup)):
        type, func, args, prename = playertup
        if type != LOCAL:
            players.append(func(*args))
            #if type == ARTIFICIAL:
            #    def readyformoves (player, color):
            #        gmwidg.setTabText(gmwidg.display_text))
            #    players[i].connect("readyForMoves", readyformoves, i)
        else:
            # Until PyChess has a proper profiles system, as discussed on the
            # issue tracker, we need to give human players special treatment
            player = func(gmwidg, *args)
            players.append(player)
            
            # Connect to conf
            if i == 0 or (i == 1 and player0tup[0] != LOCAL):
                key = "firstName"
                alt = _("You")
            else:
                key = "secondName"
                alt = _("Guest")
            if prename == conf.get(key, alt):
                conf.notify_add(key, lambda *a:player.setName(conf.get(key,alt)))

    if player0tup[0] == ARTIFICIAL and player1tup[0] == ARTIFICIAL:
        def emit_action (action, param):
            if gmwidg.isInFront():
                gamemodel.curplayer.emit("offer", Offer(action, param=param))
        gmwidg.board.connect("action", lambda b,action,param: emit_action(action, param))
    
    log.debug("ionest.workfunc: -> gamemodel.setPlayers(): %s" % (gamemodel))
    gamemodel.setPlayers(players)
    log.debug("ionest.workfunc: <- gamemodel.setPlayers(): %s" % (gamemodel))
    
    # Starting
    if loaddata:
        try:
            uri, loader, gameno, position = loaddata
            gamemodel.loadAndStart (uri, loader, gameno, position)
        except LoadingError, e:
            d = Gtk.MessageDialog (type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK,
                                    message_format=e.args[0])
            d.format_secondary_text (e.args[1])
            d.connect("response", lambda d,a: d.hide())
            worker.publish(d.show)

    else:
        if gamemodel.variant.need_initial_board:
            for player in gamemodel.players:
                player.setOptionInitialBoard(gamemodel)
        log.debug("ionest.workfunc: -> gamemodel.start(): %s" % (gamemodel))
        gamemodel.start()
        log.debug("ionest.workfunc: <- gamemodel.start(): %s" % (gamemodel))
    
    log.debug("ionest.workfunc: returning gmwidg=%s\n gamemodel=%s" % \
        (gmwidg, gamemodel))
    return gmwidg, gamemodel

################################################################################
# Global Load and Save variables                                               #
################################################################################

opendialog = None
savedialog = None
enddir = {}
saveformats = None
exportformats = None
def getOpenAndSaveDialogs():
    global opendialog, savedialog, enddir, savecombo, savers, saveformats, exportformats

    if not opendialog:
        savers = [getattr(Savers, s) for s in Savers.__all__]
        for saver in savers:
            enddir[saver.__ending__] = saver

        opendialog = Gtk.FileChooserDialog(_("Open Game"), None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        savedialog = Gtk.FileChooserDialog("", None, Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
        savedialog.set_current_folder(os.environ["HOME"])
        saveformats = Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT)
        exportformats = Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT)

        # All files filter
        star = Gtk.FileFilter()
        star.set_name(_("All Files"))
        star.add_pattern("*")
        opendialog.add_filter(star)
        auto = _("Detect type automatically")
        saveformats.append([auto, "", None])
        exportformats.append([auto, "", None])

        # All chess files filter
        all = Gtk.FileFilter()
        all.set_name(_("All Chess Files"))
        opendialog.add_filter(all)
        opendialog.set_filter(all)

        # Specific filters and save formats
        i = default = 0
        for saver in savers:
            label, ending = saver.__label__, saver.__ending__
            endstr = "(%s)" % ending
            f = Gtk.FileFilter()
            f.set_name(label+" "+endstr)
            if hasattr(enddir[ending], "load"):
                f.add_pattern("*."+ending)
                all.add_pattern("*."+ending)
                opendialog.add_filter(f)
                saveformats.append([label, endstr, saver])
                i += 1
            else:
                exportformats.append([label, endstr, saver])
            if "pgn" in endstr:
                default = i + 1

        # Add widgets to the savedialog
        savecombo = Gtk.ComboBox()
        crt = Gtk.CellRendererText()
        savecombo.pack_start(crt, True)
        savecombo.add_attribute(crt, 'text', 0)
        crt = Gtk.CellRendererText()
        savecombo.pack_start(crt, False)
        savecombo.add_attribute(crt, 'text', 1)
        savecombo.set_active(default)
        savedialog.set_extra_widget(savecombo)

        dialogBox = savedialog.get_content_area()
        enhanced_save_check  = Gtk.CheckButton(_("Save elapsed move times and analyzing engine evaluation values."))
        dialogBox.pack_end(enhanced_save_check, expand=False, fill=False, padding=0)
        keep(enhanced_save_check, "enhanced_save_check", first_value=False)
        enhanced_save_check.show()            

    return opendialog, savedialog, enddir, savecombo, savers

################################################################################
# Saving                                                                       #
################################################################################

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

def saveGameAs (game, position=None):
    opendialog, savedialog, enddir, savecombo, savers = getOpenAndSaveDialogs()

    if position is not None:
        savecombo.set_model(exportformats)
    else:
        savecombo.set_model(saveformats)

    # Keep running the dialog until the user has canceled it or made an error
    # free operation
    title = _("Save Game") if position is None else _("Export position")
    savedialog.set_title(title)
    while True:
        savedialog.set_current_name("%s %s %s" %
                                   (game.players[0], _("vs."), game.players[1]))

        res = savedialog.run()
        if res != Gtk.ResponseType.ACCEPT:
            break

        uri = savedialog.get_filename()
        ending = os.path.splitext(uri)[1]
        if ending.startswith("."): ending = ending[1:]
        append = False

        if savecombo.get_active() == 0:
            if not ending in enddir:
                d = Gtk.MessageDialog(
                        type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK)
                folder, file = os.path.split(uri)
                d.set_markup(
                          _("<big><b>Unknown file type '%s'</b></big>") % ending)
                d.format_secondary_text(_("Was unable to save '%(uri)s' as PyChess doesn't know the format '%(ending)s'.") % {
                                            'uri': uri, 'ending': ending})
                d.run()
                d.hide()
                continue
            else:
                saver = enddir[ending]
        else:
            index = savecombo.get_active()
            format = saveformats[index] if position is None else exportformats[index]
            saver = format[2]
            if not ending in enddir or not saver == enddir[ending]:
                uri += ".%s" % saver.__ending__

        if os.path.isfile(uri) and not os.access (uri, os.W_OK):
            d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK)
            d.set_markup(_("<big><b>Unable to save file '%s'</b></big>") % uri)
            d.format_secondary_text(
                _("You don't have the necessary rights to save the file.\n\
Please ensure that you have given the right path and try again."))
            d.run()
            d.hide()
            continue

        if os.path.isfile(uri):
            d = Gtk.MessageDialog(type=Gtk.MessageType.QUESTION)
            d.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, _("_Replace"),
                        Gtk.ResponseType.ACCEPT)
            if saver.__append__:
                d.add_buttons(Gtk.STOCK_ADD, 1)
            d.set_title(_("File exists"))
            folder, file = os.path.split(uri)
            d.set_markup(_("<big><b>A file named '%s' already exists. Would you like to replace it?</b></big>") % file)
            d.format_secondary_text(_("The file already exists in '%s'. If you replace it, its content will be overwritten.") % folder)
            replaceRes = d.run()
            d.hide()

            if replaceRes == 1:
                append = True
            elif replaceRes == Gtk.ResponseType.CANCEL:
                continue
        else:
            print repr(uri)
        try:
            game.save(uri, saver, append, position)
        except IOError, e:
            d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR)
            d.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
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

################################################################################
# Closing                                                                      #
################################################################################
def closeAllGames (pairs):
    changedPairs = [(gmwidg, game) for gmwidg, game in pairs if game.isChanged()]
    if len(changedPairs) == 0:
        response = Gtk.ResponseType.OK

    #if conf.get("autoSave", False): # Autosave option from preferences?
        #for gmwidg, game in changedPairs:
            #game.save(None, Savers.database, append=False)
        #response = Gtk.ResponseType.OK
    #else:
    
    elif len(changedPairs) == 1:
        response = closeGame(*changedPairs[0])
    else:
        widgets = GladeWidgets("saveGamesDialog.glade")
        dialog = widgets["saveGamesDialog"]
        heading = widgets["saveGamesDialogHeading"]
        saveLabel = widgets["saveGamesDialogSaveLabel"]
        treeview = widgets["saveGamesDialogTreeview"]

        heading.set_markup("<big><b>" +
                           ngettext("There is %d game with unsaved moves.",
                              "There are %d games with unsaved moves.",
                              len(changedPairs)) % len(changedPairs) +
                           " " + _("Save moves before closing?") +
                           "</b></big>")

        liststore = Gtk.ListStore(bool, str)
        treeview.set_model(liststore)
        renderer = Gtk.CellRendererToggle()
        renderer.props.activatable = True
        treeview.append_column(Gtk.TreeViewColumn("", renderer, active=0))
        treeview.append_column(Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=1))
        for gmwidg, game in changedPairs:
            liststore.append((True, "%s %s %s" %
                             (game.players[0], _("vs."), game.players[1])))

        def callback (cell, path):
            if path:
                liststore[path][0] = not liststore[path][0]
            saves = len(tuple(row for row in liststore if row[0]))
            saveLabel.set_text(ngettext("_Save %d document", "_Save %d documents", saves) % saves)
            saveLabel.set_use_underline(True)
        renderer.connect("toggled", callback)

        callback(None, None)

        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.YES:
                for i in xrange(len(liststore)-1, -1, -1):
                    checked, name = liststore[i]
                    if checked:
                        gmwidg, game = changedPairs[i]
                        if saveGame(game) == Gtk.ResponseType.ACCEPT:
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

    if response not in (Gtk.ResponseType.DELETE_EVENT, Gtk.ResponseType.CANCEL):
        for gmwidg, game in pairs:
            game.end(ABORTED, ABORTED_AGREEMENT)
            game.terminate()

    return response

def closeGame (gmwidg, game):
    if not game.isChanged():
        response = Gtk.ResponseType.OK
    else:
        #if conf.get("autoSave", False): # Autosave option from preferences?
            #game.save(None, Savers.database, append=False)
            #response = Gtk.ResponseType.OK
        #else
        
        d = Gtk.MessageDialog (type = Gtk.MessageType.WARNING)
        d.add_button(_("Close _without Saving"), Gtk.ResponseType.OK)
        d.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        if game.uri:
            d.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.YES)
        else: d.add_button(Gtk.STOCK_SAVE_AS, Gtk.ResponseType.YES)

        gmwidg.bringToFront()

        d.set_markup(_("<b><big>Save the current game before you close it?</big></b>"))
        d.format_secondary_text (_(
            "It is not possible later to continue the game,\nif you don't save it."))
        
        response = d.run()
        d.destroy()

        if response == Gtk.ResponseType.YES:
            # Test if cancel was pressed in the save-file-dialog
            if saveGame(game) != Gtk.ResponseType.ACCEPT:
                response = Gtk.ResponseType.CANCEL

    if response not in (Gtk.ResponseType.DELETE_EVENT, Gtk.ResponseType.CANCEL):
        if game.status in UNFINISHED_STATES:
            game.end(ABORTED, ABORTED_AGREEMENT)
        game.terminate()
        gamewidget.delGameWidget (gmwidg)

    return response

################################################################################
# Signal handler                                                               #
################################################################################


class Handler (GObject.GObject):
    """ The goal of this class, is to provide signal handling for the ionest
        module.
        Emit objects are gmwidg, gameobject """

    __gsignals__ = {
        'gmwidg_created': (GObject.SignalFlags.RUN_FIRST, None, (object, object))
    }

    def __init__ (self):
        GObject.GObject.__init__(self)

handler = Handler()
