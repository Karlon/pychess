import os
from struct import Struct
from collections import namedtuple

from pychess.Utils.const import *
from pychess.System.prefix import addDataPrefix
from pychess.Utils.lutils.lmove import parsePolyglot

# The book probing code is based on that of PolyGlot by Fabien Letouzey.
# PolyGlot is available under the GNU GPL from http://wbec-ridderkerk.nl

BookEntry = namedtuple('BookEntry', 'key move weight games score')
# 'key' c_uint64      the position's hash
# 'move' c_uint16     the candidate move
# 'weight' c_uint16   proportional to prob. we should play it
# The following terms are not always available:
# 'games' c_uint16    the number of times it's been tried
# 'score' c_uint16    2 for each win, 1 for each draw

entrystruct = Struct(">QHHHH")
entrysize = entrystruct.size

def getOpenings (board):
    """ Return a tuple (move, weight, games, score) for each opening move
        in the given position. The weight is proportional to the probability
        that a move should be played. By convention, games is the number of
        times a move has been tried, and score the number of points it has
        scored (with 2 per victory and 1 per draw). However, opening books
        aren't required to keep this information. """
    path = os.path.join(addDataPrefix("pychess_book.bin"))
    openings = list()
    with open(path, "rb") as bookFile:
        key = board.hash
        # Find the first entry whose key is >= the position's hash
        bookFile.seek(0, os.SEEK_END)
        lo, hi = 0, bookFile.tell() / 16 - 1
        if hi < 0:
            return openings
        while lo < hi:
            mid = (lo + hi) / 2
            bookFile.seek(mid * 16)
            entry = BookEntry._make(entrystruct.unpack(bookFile.read(entrysize)))
            if entry.key < key:
                lo = mid + 1
            else:
                hi = mid

        bookFile.seek(lo * 16)
        while True:
            entry = BookEntry._make(entrystruct.unpack(bookFile.read(entrysize)))
            if entry.key != key:
                break
            mv = parsePolyglot(board, entry.move)
            openings.append( ( mv, entry.weight, entry.games, entry.score ) )
    return openings
