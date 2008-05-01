# Chess960 (Fischer Random Chess)
# http://en.wikipedia.org/wiki/Chess960

import random

from pychess.Utils.Board import Board as NormalBoard
from pychess.Utils.const import *


class FRCBoard(NormalBoard):
    def __init__ (self, setup=False):
        if setup is True:
            NormalBoard.__init__(self, setup=shuffle_start())
        else:
            NormalBoard.__init__(self, setup=setup)

    def move_castling_rook(self, flag, newBoard):
        if self.color == WHITE:
            if flag == QUEEN_CASTLE:
                newBoard[Cord(D1)] = newBoard[Cord(self.ini_rooks[0][0])]
                newBoard[Cord(self.ini_rooks[0][0])] = None
            elif flag == KING_CASTLE:
                newBoard[Cord(F1)] = newBoard[Cord(self.ini_rooks[0][1])]
                newBoard[Cord(self.ini_rooks[0][1])] = None
        else:
            if flag == QUEEN_CASTLE:
                newBoard[Cord(D8)] = newBoard[Cord(self.ini_rooks[1][0])]
                newBoard[Cord(self.ini_rooks[1][0])] = None
            elif flag == KING_CASTLE:
                newBoard[Cord(F8)] = newBoard[Cord(self.ini_rooks[1][1])]
                newBoard[Cord(self.ini_rooks[1][1])] = None


class FischerRandomChess:
    name = _("Fischer Random")
    board = FRCBoard


def shuffle_start():
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

    return tmp


if __name__ == '__main__':
    for i in range(10):
        print shuffle_start()
