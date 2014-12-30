from __future__ import absolute_import
from .const import *

from pychess.compat import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda s: s


reprColor = [_("White"), _("Black")]

reprPiece = ["Empty", _("Pawn"), _("Knight"), _("Bishop"), _("Rook"), _("Queen"), _("King"), "BPawn"]

localReprSign = ["", _("P"), _("N"), _("B"), _("R"), _("Q"), _("K")]

reprResult_long = {
    DRAW: _("The game ended in a draw"),
    WHITEWON: _("%(white)s won the game"),
    BLACKWON: _("%(black)s won the game"),
    KILLED: _("The game has been killed"),
    ADJOURNED: _("The game has been adjourned"),
    ABORTED: _("The game has been aborted"),
}

reprReason_long = {
    DRAW_INSUFFICIENT: _("Because neither player has sufficient material to mate"),
    DRAW_REPITITION: _("Because the same position was repeated three times in a row"),
    DRAW_50MOVES: _("Because the last 50 moves brought nothing new"),
    DRAW_CALLFLAG: _("Because both players ran out of time"),
    DRAW_STALEMATE: _("Because %(mover)s stalemated"),
    DRAW_AGREE: _("Because both players agreed to a draw"),
    DRAW_ADJUDICATION: _("Because of adjudication by an admin"),
    DRAW_LENGTH: _("Because the game exceed the max length"),
    DRAW_BLACKINSUFFICIENTANDWHITETIME: _("Because %(white)s ran out of time and %(black)s has insufficient material to mate"),
    DRAW_WHITEINSUFFICIENTANDBLACKTIME: _("Because %(black)s ran out of time and %(white)s has insufficient material to mate"),
    DRAW_EQUALMATERIAL: _("Because both players have the same amount of pieces"),

    WON_RESIGN: _("Because %(loser)s resigned"),
    WON_CALLFLAG: _("Because %(loser)s ran out of time"),
    WON_MATE: _("Because %(loser)s was checkmated"),
    WON_DISCONNECTION: _("Because %(loser)s disconnected"),
    WON_ADJUDICATION:  _("Because of adjudication by an admin"),
    WON_LESSMATERIAL: _("Because %(winner)s has fewer pieces"),
    WON_NOMATERIAL: _("Because %(winner)s lost all pieces"),
    WON_KINGEXPLODE: _("Because %(loser)s king exploded"),
    WON_KINGINCENTER: _("Because %(winner)s king reached the center"),

    ADJOURNED_LOST_CONNECTION: _("Because a player lost connection"),
    ADJOURNED_AGREEMENT: _("Because both players agreed to an adjournment"),
    ADJOURNED_SERVER_SHUTDOWN: _("Because the server was shut down"),
    ADJOURNED_COURTESY: _("Because a player lost connection and the other player requested adjournment"),
    ADJOURNED_COURTESY_WHITE: _("Because %(black)s lost connection to the server and %(white)s requested adjournment"),
    ADJOURNED_COURTESY_BLACK: _("Because %(white)s lost connection to the server and %(black)s requested adjournment"),
    ADJOURNED_LOST_CONNECTION_WHITE: _("Because %(white)s lost connection to the server"),
    ADJOURNED_LOST_CONNECTION_BLACK: _("Because %(black)s lost connection to the server"),

    ABORTED_ADJUDICATION: _("Because of adjudication by an admin. No rating changes have occurred."),
    ABORTED_AGREEMENT: _("Because both players agreed to abort the game. No rating changes have occurred."),
    ABORTED_COURTESY: _("Because of courtesy by a player. No rating changes have occurred."),
    ABORTED_EARLY: _("Because a player aborted the game. Either player can abort the game without the other's consent before the second move. No rating changes have occurred."),
    ABORTED_DISCONNECTION: _("Because a player disconnected and there are too few moves to warrant adjournment. No rating changes have occurred."),
    ABORTED_SERVER_SHUTDOWN: _("Because the server was shut down. No rating changes have occurred."),

    WHITE_ENGINE_DIED: _("Because the %(white)s engine died"),
    BLACK_ENGINE_DIED: _("Because the %(black)s engine died"),
    DISCONNECTED: _("Because the connection to the server was lost"),
    UNKNOWN_REASON: _("The reason is unknown")
}
