""" This module intends to work as glue between the gamemodel and the gamewidget
    taking care of stuff that is neither very offscreen nor very onscreen
    like bringing up dialogs and """

import math

import gtk

from pychess.ic.ICGameModel import ICGameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import *
from pychess.Utils.repr import reprResult_long, reprReason_long
from pychess.System import conf
from pychess.System import glock
from pychess.System.Log import log
from pychess.widgets import preferencesDialog

from gamewidget import getWidgets, key2gmwidg, isDesignGWShown

def nurseGame (gmwidg, gamemodel):
    """ Call this function when gmwidget is just created """
    
    gmwidg.connect("infront", on_gmwidg_infront)
    gmwidg.connect("closed", on_gmwidg_closed)
    gmwidg.connect("title_changed", on_gmwidg_title_changed)
    
    # Because of the async loading of games, the game might already be started,
    # when the glock is ready and nurseGame is called.
    # Thus we support both cases.
    if gamemodel.status == WAITING_TO_START:
        gamemodel.connect("game_started", on_game_started, gmwidg)
        gamemodel.connect("game_loaded", game_loaded, gmwidg)
    else:
        if gamemodel.uri:
            game_loaded(gamemodel, gamemodel.uri, gmwidg)
        on_game_started(gamemodel, gmwidg)
    
    gamemodel.connect("game_saved", game_saved, gmwidg)
    gamemodel.connect("game_ended", game_ended, gmwidg)
    gamemodel.connect("game_unended", game_unended, gmwidg)
    gamemodel.connect("game_resumed", game_unended, gmwidg)
    gamemodel.connect("game_changed", game_changed, gmwidg)
    gamemodel.connect("game_paused", game_paused, gmwidg)

#===============================================================================
# Gamewidget signals
#===============================================================================

def on_gmwidg_infront (gmwidg):
    for widget in MENU_ITEMS:
        if widget in gmwidg.menuitems:
            continue
        elif widget == 'show_sidepanels' and isDesignGWShown():
            getWidgets()[widget].set_property('sensitive', False)
        else:
            getWidgets()[widget].set_property('sensitive', True)
    
    # Change window title
    getWidgets()['window1'].set_title('%s - PyChess' % gmwidg.getTabText())
    return False

def on_gmwidg_closed (gmwidg):
    if len(key2gmwidg) == 1:
        getWidgets()['window1'].set_title('%s - PyChess' % _('Welcome'))
    return False

def on_gmwidg_title_changed (gmwidg):
    if gmwidg.isInFront():
        getWidgets()['window1'].set_title('%s - PyChess' % gmwidg.getTabText())
    return False

#===============================================================================
# Gamemodel signals
#===============================================================================

def game_ended (gamemodel, reason, gmwidg):
    log.debug("gamenanny.game_ended: reason=%s gmwidg=%s\ngamemodel=%s\n" % \
        (reason, gmwidg, gamemodel))
    nameDic = {"white": gamemodel.players[WHITE],
               "black": gamemodel.players[BLACK],
               "mover": gamemodel.curplayer}
    if gamemodel.status == WHITEWON:
        nameDic["winner"] = gamemodel.players[WHITE]
        nameDic["loser"] = gamemodel.players[BLACK]
    elif gamemodel.status == BLACKWON:
        nameDic["winner"] = gamemodel.players[BLACK]
        nameDic["loser"] = gamemodel.players[WHITE]
    
    m1 = reprResult_long[gamemodel.status] % nameDic
    m2 = reprReason_long[reason] % nameDic
    
    
    md = gtk.MessageDialog()
    md.set_markup("<b><big>%s</big></b>" % m1)
    md.format_secondary_markup(m2)
    
    if gamemodel.players[0].__type__ == LOCAL or gamemodel.players[1].__type__ == LOCAL:
        if gamemodel.players[0].__type__ == REMOTE or gamemodel.players[1].__type__ == REMOTE:
            md.add_button(_("Offer Rematch"), 0)
        else:
            md.add_button(_("Play Rematch"), 1)
            if gamemodel.status in UNDOABLE_STATES and gamemodel.reason in UNDOABLE_REASONS:
                if gamemodel.ply == 1:
                    md.add_button(_("Undo one move"), 2)
                elif gamemodel.ply > 1:
                    md.add_button(_("Undo two moves"), 2)
    
    def cb (messageDialog, responseId):
        if responseId == 0:
            if gamemodel.players[0].__type__ == REMOTE:
                gamemodel.players[0].offerRematch()
            else:
                gamemodel.players[1].offerRematch()
        elif responseId == 1:
            # newGameDialog uses ionest uses gamenanny uses newGameDialog...
            from pychess.widgets.newGameDialog import createRematch
            createRematch(gamemodel)
        elif responseId == 2:
            if gamemodel.curplayer.__type__ == LOCAL and gamemodel.ply > 1:
                offer = Offer(TAKEBACK_OFFER, gamemodel.ply-2)
            else:
                offer = Offer(TAKEBACK_OFFER, gamemodel.ply-1)
            if gamemodel.players[0].__type__ == LOCAL:
                gamemodel.players[0].emit("offer", offer)
            else: gamemodel.players[1].emit("offer", offer)
    md.connect("response", cb)
    
    glock.acquire()
    try:
        gmwidg.showMessage(md)
        gmwidg.status("%s %s." % (m1,m2[0].lower()+m2[1:]))
        
        if reason == WHITE_ENGINE_DIED:
            engineDead(gamemodel.players[0], gmwidg)
        elif reason == BLACK_ENGINE_DIED:
            engineDead(gamemodel.players[1], gmwidg)
    finally:
        glock.release()
    
    return False

def _set_statusbar (gamewidget, message):
    assert type(message) is str or type(message) is unicode
    gamewidget.status(message)
    
def game_paused (gamemodel, gmwidg):
    s = _("The game is paused")
    _set_statusbar(gmwidg, s)
    return False
    
def game_changed (gamemodel, gmwidg):
    _set_statusbar(gmwidg, "")
    return False
    
def game_unended (gamemodel, gmwidg):
    log.debug("gamenanny.game_unended: %s\n" % gamemodel.boards[-1])
    glock.acquire()
    try:
        gmwidg.hideMessage()
    finally:
        glock.release()
    _set_statusbar(gmwidg, "")
    return False

# Connect game_loaded, game_saved and game_ended to statusbar
def game_loaded (gamemodel, uri, gmwidg):
    if type(uri) in (str, unicode):
        s = "%s: %s" % (_("Loaded game"), str(uri))
    else: s = _("Loaded game")
    
    _set_statusbar(gmwidg, s)
    return False

def game_saved (gamemodel, uri, gmwidg):
    _set_statusbar(gmwidg, "%s: %s" % (_("Saved game"), str(uri)))
    return False

def analyzer_added (gamemodel, analyzer, analyzer_type, gmwidg):
    s = _("Analyzer started") + ": " + analyzer.name
    _set_statusbar(gmwidg, s)
    return False

def on_game_started (gamemodel, gmwidg):
    on_gmwidg_infront(gmwidg)  # setup menu items sensitivity

    # Rotate to human player
    boardview = gmwidg.board.view
    if gamemodel.players[1].__type__ == LOCAL:
        if gamemodel.players[0].__type__ != LOCAL:
            boardview.rotation = math.pi
        elif conf.get("autoRotate", True) and \
                gamemodel.curplayer == gamemodel.players[1]:
            boardview.rotation = math.pi
    
    # Play set-up sound
    preferencesDialog.SoundTab.playAction("gameIsSetup")
    
    # Connect player offers to statusbar
    for player in gamemodel.players:
        if player.__type__ == LOCAL:
            player.connect("offer", offer_callback, gamemodel, gmwidg)
    
    # Start analyzers if any
    gamemodel.connect("analyzer_added", analyzer_added, gmwidg)
    if not (isinstance(gamemodel, ICGameModel) and \
            gamemodel.isObservationGame() is False):
        gamemodel.start_analyzer(HINT)
        gamemodel.start_analyzer(SPY)
    
    return False

#===============================================================================
# Player signals
#===============================================================================

def offer_callback (player, offer, gamemodel, gmwidg):
    if gamemodel.status != RUNNING:
        # If the offer has already been handled by Gamemodel and the game was
        # drawn, we need to do nothing
        return

    message = ""
    if offer.type == ABORT_OFFER:
        message = _("You sent an abort offer")
    elif offer.type == ADJOURN_OFFER:
        message = _("You sent an adjournment offer")
    elif offer.type == DRAW_OFFER:
        message = _("You sent a draw offer")
    elif offer.type == PAUSE_OFFER:
        message = _("You sent a pause offer")
    elif offer.type == RESUME_OFFER:
        message = _("You sent a resume offer")
    elif offer.type == TAKEBACK_OFFER:
        message = _("You sent an undo offer")
    elif offer.type == HURRY_ACTION:
        message = _("You asked your opponent to move")
    
    _set_statusbar(gmwidg, message)
    return False

#===============================================================================
# Subfunctions
#===============================================================================

def engineDead (engine, gmwidg):
    gmwidg.bringToFront()
    d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
    d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()
