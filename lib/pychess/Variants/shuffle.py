# Shuffle Chess
# http://en.wikipedia.org/wiki/Chess960#Other_related_chess_variants

import random

from pychess.Utils.Board import Board as NormalBoard


class ShuffleBoard(NormalBoard):
    def __init__ (self, setup=False):
        if setup is True:
            NormalBoard.__init__(self, setup=shuffle_start())
        else:
            NormalBoard.__init__(self, setup=setup)


class ShuffleChess:
    board = ShuffleBoard


def shuffle_start():
    """ Create a random initial position.
        No additional restrictions.
        Castling only possible when king and rook are
        on their traditional starting squares."""
    
    tmp = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
    random.shuffle(tmp)
    tmp = ''.join(tmp)
    tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w KQkq - 0 1'
    
    # TODO: adjust castling
    
    return tmp


if __name__ == '__main__':
    for i in range(10):
        print shuffle_start()
