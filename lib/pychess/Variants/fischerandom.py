# Chess960 (Fischer Random Chess)
# http://en.wikipedia.org/wiki/Chess960

import random

# used only for selftesting
#import __builtin__
#__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import *
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.lutils.bitboard import *
from pychess.Utils.lutils.attack import *

from pychess.Utils.lutils.lmove import newMove


class FRCBoard(Board):

    variant = FISCHERRANDOMCHESS
    
    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start())
        else:
            Board.__init__(self, setup=setup)

    def move_castling_rook(self, flag, newBoard):
        if self.color == WHITE:
            if flag == QUEEN_CASTLE:
                newBoard[Cord(D1)] = newBoard[Cord(self.board.ini_rooks[0][0])]
                newBoard[Cord(self.board.ini_rooks[0][0])] = None
            elif flag == KING_CASTLE:
                newBoard[Cord(F1)] = newBoard[Cord(self.board.ini_rooks[0][1])]
                newBoard[Cord(self.board.ini_rooks[0][1])] = None
        else:
            if flag == QUEEN_CASTLE:
                newBoard[Cord(D8)] = newBoard[Cord(self.board.ini_rooks[1][0])]
                newBoard[Cord(self.board.ini_rooks[1][0])] = None
            elif flag == KING_CASTLE:
                newBoard[Cord(F8)] = newBoard[Cord(self.board.ini_rooks[1][1])]
                newBoard[Cord(self.board.ini_rooks[1][1])] = None

    def shuffle_start(self):
        """ Create a random initial position.
            The king is placed somewhere between the two rooks.
            The bishops are placed on opposite-colored squares."""
      
        positions = [1, 2, 3, 4, 5, 6, 7, 8]
        tmp = [''] * 8

        bishop = random.choice((1, 3, 5, 7))
        tmp[bishop-1] = 'b'
        positions.remove(bishop)

        bishop = random.choice((2, 4, 6, 8))
        tmp[bishop-1] = 'b'
        positions.remove(bishop)

        queen = random.choice(positions)
        tmp[queen-1] = 'q'
        positions.remove(queen)

        knight = random.choice(positions)
        tmp[knight-1] = 'n'
        positions.remove(knight)

        knight = random.choice(positions)
        tmp[knight-1] = 'n'
        positions.remove(knight)

        rook = positions[0]
        tmp[rook-1] = 'r'

        king = positions[1]
        tmp[king-1] = 'k'

        rook = positions[2]
        tmp[rook-1] = 'r'

        tmp = ''.join(tmp)
        tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w KQkq - 0 1'
        # TODO: remove
        tmp = "brqknnrb/pppppppp/8/8/8/8/PPPPPPPP/BRQKNNRB w KQkq - 0 1"
        
        return tmp


class FischerRandomChess:
    name = _("Fischer Random")
    board = FRCBoard


def frc_castling_moves(board):
    if board.color == WHITE:
        if board.castling & W_OO:
            blocker = clearBit(board.blocker, board.ini_rooks[WHITE][1])
            if board.ini_kings[WHITE] == B1 and not fromToRay[B1][G1] & blocker and \
                not isAttacked (board, B1, BLACK) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (B1, G1, KING_CASTLE)

            if board.ini_kings[WHITE] == C1 and not fromToRay[C1][G1] & blocker and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (C1, G1, KING_CASTLE)

            if board.ini_kings[WHITE] == D1 and not fromToRay[D1][G1] & blocker and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (D1, G1, KING_CASTLE)

            if board.ini_kings[WHITE] == E1 and not fromToRay[E1][G1] & blocker and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (E1, G1, KING_CASTLE)

            if board.ini_kings[WHITE] == F1 and not fromToRay[F1][G1] & blocker and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (F1, G1, KING_CASTLE)
        
            if board.ini_kings[WHITE] == G1 and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (G1, G1, KING_CASTLE)

        if board.castling & W_OOO:
            blocker = clearBit(board.blocker, board.ini_rooks[WHITE][0])
            if board.ini_kings[WHITE] == G1 and not fromToRay[G1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    yield newMove (G1, C1, QUEEN_CASTLE)

            if board.ini_kings[WHITE] == F1 and not fromToRay[F1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK):
                    yield newMove (F1, C1, QUEEN_CASTLE)

            if board.ini_kings[WHITE] == E1 and not fromToRay[E1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK):
                    yield newMove (E1, C1, QUEEN_CASTLE)

            if board.ini_kings[WHITE] == D1 and not fromToRay[D1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK):
                    yield newMove (D1, C1, QUEEN_CASTLE)

            if board.ini_kings[WHITE] == C1 and \
                board.arBoard[D1] == EMPTY and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK):
                    yield newMove (C1, C1, QUEEN_CASTLE)

            if board.ini_kings[WHITE] == B1 and \
                board.arBoard[C1] == EMPTY and \
                board.arBoard[D1] == EMPTY and \
                not isAttacked (board, B1, BLACK) and \
                not isAttacked (board, C1, BLACK):
                    yield newMove (B1, C1, QUEEN_CASTLE)

    else:
        if board.castling & B_OO:
            blocker = clearBit(board.blocker, board.ini_rooks[BLACK][1])
            if board.ini_kings[BLACK] == B8 and not fromToRay[B8][G8] & blocker and \
                not isAttacked (board, B8, BLACK) and \
                not isAttacked (board, C8, BLACK) and \
                not isAttacked (board, D8, BLACK) and \
                not isAttacked (board, E8, BLACK) and \
                not isAttacked (board, F8, BLACK) and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (B8, G8, KING_CASTLE)

            if board.ini_kings[BLACK] == C8 and not fromToRay[C8][G8] & blocker and \
                not isAttacked (board, C8, BLACK) and \
                not isAttacked (board, D8, BLACK) and \
                not isAttacked (board, E8, BLACK) and \
                not isAttacked (board, F8, BLACK) and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (C8, G8, KING_CASTLE)

            if board.ini_kings[BLACK] == D8 and not fromToRay[D8][G8] & blocker and \
                not isAttacked (board, D8, BLACK) and \
                not isAttacked (board, E8, BLACK) and \
                not isAttacked (board, F8, BLACK) and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (D8, G8, KING_CASTLE)

            if board.ini_kings[BLACK] == E8 and not fromToRay[E8][G8] & blocker and \
                not isAttacked (board, E8, BLACK) and \
                not isAttacked (board, F8, BLACK) and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (E8, G8, KING_CASTLE)

            if board.ini_kings[BLACK] == F8 and not fromToRay[F8][G8] & blocker and \
                not isAttacked (board, F8, BLACK) and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (F8, G8, KING_CASTLE)
        
            if board.ini_kings[BLACK] == G8 and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (G8, G8, KING_CASTLE)

        if board.castling & B_OOO:
            blocker = clearBit(board.blocker, board.ini_rooks[BLACK][0])
            if board.ini_kings[BLACK] == G8 and not fromToRay[G8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, BLACK) and \
                not isAttacked (board, D8, BLACK) and \
                not isAttacked (board, E8, BLACK) and \
                not isAttacked (board, F8, BLACK) and \
                not isAttacked (board, G8, BLACK):
                    yield newMove (G8, C8, QUEEN_CASTLE)

            if board.ini_kings[BLACK] == F8 and not fromToRay[F8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, BLACK) and \
                not isAttacked (board, D8, BLACK) and \
                not isAttacked (board, E8, BLACK) and \
                not isAttacked (board, F8, BLACK):
                    yield newMove (F8, C8, QUEEN_CASTLE)

            if board.ini_kings[BLACK] == E8 and not fromToRay[E8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, BLACK) and \
                not isAttacked (board, D8, BLACK) and \
                not isAttacked (board, E8, BLACK):
                    yield newMove (E8, C8, QUEEN_CASTLE)

            if board.ini_kings[BLACK] == D8 and not fromToRay[D8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, BLACK) and \
                not isAttacked (board, D8, BLACK):
                    yield newMove (D8, C8, QUEEN_CASTLE)

            if board.ini_kings[BLACK] == C8 and \
                board.arBoard[D8] == EMPTY and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, BLACK):
                    yield newMove (C8, C8, QUEEN_CASTLE)

            if board.ini_kings[BLACK] == B8 and not fromToRay[B8][C8] & blocker and \
                board.arBoard[C8] == EMPTY and \
                board.arBoard[D8] == EMPTY and \
                not isAttacked (board, B8, BLACK) and \
                not isAttacked (board, C8, BLACK):
                    yield newMove (B8, C8, QUEEN_CASTLE)


if __name__ == '__main__':
    frcBoard = FRCBoard(True)
    for i in range(10):
        print frcBoard.shuffle_start()
