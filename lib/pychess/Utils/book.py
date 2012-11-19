import os
from ctypes import *

from pychess.Utils.const import *
from pychess.System import conf
from pychess.System.prefix import addDataPrefix
from pychess.Utils.lutils.lmove import parsePolyglot

# The book probing code is based on that of PolyGlot by Fabien Letouzey.
# PolyGlot is available under the GNU GPL from http://wbec-ridderkerk.nl

class BookEntry(BigEndianStructure):
    _fields_ = [ ('key', c_uint64),    # the position's hash
                 ('move', c_uint16),   # the candidate move
                 ('weight', c_uint16), # proportional to prob. we should play it
                 # The following terms are not always available:
                 ('games', c_uint16),  # the number of times it's been tried
                 ('score', c_uint16)   # 2 for each win, 1 for each draw
               ]


def getOpenings (board):
    """ Return a tuple (move, weight, games, score) for each opening move
        in the given position. The weight is proportional to the probability
        that a move should be played. By convention, games is the number of
        times a move has been tried, and score the number of points it has
        scored (with 2 per victory and 1 per draw). However, opening books
        aren't required to keep this information. """

    if not conf.get("opening_check", 0):
        return []
        
    default_path = os.path.join(addDataPrefix("pychess_book.bin"))
    path = path = conf.get("opening_file_entry", default_path) 

    openings = []
    with open(path, "rb") as bookFile:
        key = board.hash
        entry = BookEntry()
        # Find the first entry whose key is >= the position's hash
        bookFile.seek(0, os.SEEK_END)
        lo, hi = 0, bookFile.tell() / 16 - 1
        if hi < 0:
            return openings
        while lo < hi:
            mid = (lo + hi) / 2
            bookFile.seek(mid * 16)
            bookFile.readinto(entry)
            if entry.key < key:
                lo = mid + 1
            else:
                hi = mid

        bookFile.seek(lo * 16)
        while bookFile.readinto(entry) == 16:
            if entry.key != key:
                break
            mv = parsePolyglot(board, entry.move)
            openings.append( ( mv, entry.weight, entry.games, entry.score ) )
    return openings
