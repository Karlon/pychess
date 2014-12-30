""" This module contains chess logic functins for the pychess client. They are
    based upon the lutils modules, but supports standard object types and is
    therefore not as fast. """
from __future__ import absolute_import

from .lutils import lmovegen
from .lutils.validator import validateMove
from .lutils.lmove import FCORD, TCORD
from .lutils import ldraw
from .Cord import Cord
from .Move import Move
from .const import *
from .lutils.bitboard import iterBits
from .lutils.attack import getAttacks
from pychess.Variants.suicide import pieceCount
from pychess.Variants.losers import testKingOnly
from pychess.Variants.atomic import kingExplode
from pychess.Variants.kingofthehill import testKingInCenter


def getDestinationCords (board, cord):
    tcords = []
    for move in lmovegen.genAllMoves (board.board):
        if FCORD(move) == cord.cord:
            if not board.board.willLeaveInCheck(move):
                tcords.append(Cord(TCORD(move)))
    return tcords

def isClaimableDraw (board):
    lboard = board.board
    if lboard.repetitionCount () >= 3:
        return True
    if ldraw.testFifty (lboard):
        return True
    return False

def playerHasMatingMaterial (board, playercolor):
    lboard = board.board
    return ldraw.testPlayerMatingMaterial(lboard, playercolor)

def getStatus (board):
    lboard = board.board

    if board.variant == LOSERSCHESS:
        if testKingOnly(lboard):
            if board.color == WHITE:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_NOMATERIAL
    elif board.variant == SUICIDECHESS:
        if pieceCount(lboard, lboard.color) == 0:
            if board.color == WHITE:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_NOMATERIAL
    elif board.variant == ATOMICCHESS:
        if lboard.boards[board.color][KING] == 0:
            if board.color == WHITE:
                status = BLACKWON
            else:
                status = WHITEWON
            return status, WON_KINGEXPLODE
    elif board.variant == KINGOFTHEHILLCHESS:
        if testKingInCenter(lboard):
            if board.color == BLACK:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_KINGINCENTER
    else:
        if ldraw.testMaterial (lboard):
            return DRAW, DRAW_INSUFFICIENT
    
    hasMove = False
    for move in lmovegen.genAllMoves (lboard):
        if board.variant == ATOMICCHESS:
            if kingExplode(lboard, move, 1-board.color) and not kingExplode(lboard, move, board.color):
                hasMove = True
                break
            elif kingExplode(lboard, move, board.color):
                continue
        lboard.applyMove(move)
        if lboard.opIsChecked():
            lboard.popMove()
            continue
        hasMove = True
        lboard.popMove()
        break

    if not hasMove:
        if lboard.isChecked():
            if board.variant == LOSERSCHESS:
                if board.color == WHITE:
                    status = WHITEWON
                else:
                    status = BLACKWON
            else:
                if board.color == WHITE:
                    status = BLACKWON
                else:
                    status = WHITEWON
            return status, WON_MATE
        else:
            if board.variant == LOSERSCHESS:
                if board.color == WHITE:
                    status = WHITEWON
                else:
                    status = BLACKWON
                return status, DRAW_STALEMATE
            elif board.variant == SUICIDECHESS:
                if pieceCount(lboard, WHITE) == pieceCount(lboard, BLACK):
                    return status, DRAW_EQUALMATERIAL
                else:
                    if board.color == WHITE and pieceCount(lboard, WHITE) < pieceCount(lboard, BLACK):
                        status = WHITEWON
                    else:
                        status = BLACKWON
                    return status, WON_LESSMATERIAL
            else:
                return DRAW, DRAW_STALEMATE

    if lboard.repetitionCount () >= 3:
        return DRAW, DRAW_REPITITION
    
    if ldraw.testFifty (lboard):
        return DRAW, DRAW_50MOVES

    return RUNNING, UNKNOWN_REASON
    
def standard_validate (board, move):
    return validateMove (board.board, move.move) and \
           not board.board.willLeaveInCheck(move.move)

def validate (board, move):
    if board.variant == LOSERSCHESS:
        capture = move.flag == ENPASSANT or board[move.cord1] != None
        if capture:
            return standard_validate (board, move)
        else:
            can_capture = False
            can_escape_with_capture= False
            ischecked = board.board.isChecked()
            for c in lmovegen.genCaptures(board.board):
                if board.board.willLeaveInCheck(c):
                    continue
                else:
                    can_capture = True
                    if ischecked:
                        can_escape_with_capture = True
                    break
            if can_capture:
                if ischecked and not can_escape_with_capture:
                    return standard_validate (board, move)
                else:
                    return False
            else:
                return standard_validate (board, move)
    elif board.variant == SUICIDECHESS:
        capture = move.flag == ENPASSANT or board[move.cord1] != None
        if capture:
            return standard_validate (board, move)
        else:
            can_capture = False
            for c in lmovegen.genCaptures(board.board):
                from pychess.Utils.Move import Move
                can_capture = True
                #break
            if can_capture:
                return False
            else:
                return standard_validate (board, move)
    elif board.variant == ATOMICCHESS:
        # Moves exploding our king are not allowed
        if kingExplode(board.board, move.move, board.color):
            return False
        # Exploding oppont king takes precedence over mate
        elif kingExplode(board.board, move.move, 1-board.color) and validateMove(board.board, move.move):
            return True
        else:
            return standard_validate (board, move)
    else:
        return standard_validate (board, move)

def getMoveKillingKing (board):
    """ Returns a move from the current color, able to capture the opponent
        king """
    
    lboard = board.board
    color = lboard.color
    opking = lboard.kings[1-color]
    
    for cord in iterBits (getAttacks(lboard, opking, color)):
        return Move(Cord(cord), Cord(opking), board)

def genCastles (board):
    for move in lmovegen.genCastles(board.board):
        yield Move(move)

def legalMoveCount (board):
    moves = 0
    for move in lmovegen.genAllMoves (board.board):
        if not board.board.willLeaveInCheck(move):
            moves += 1
    return moves
