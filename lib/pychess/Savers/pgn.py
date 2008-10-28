import re
import datetime

from pychess.Utils.Move import *
from pychess.Utils.const import *
from pychess.System.Log import log
from pychess.Utils.logic import getStatus
from pychess.Utils.Board import Board
from pychess.Utils.GameModel import GameModel
from pychess.Variants.fischerandom import FischerRandomChess

from ChessFile import ChessFile, LoadingError

__label__ = _("Chess Game")
__endings__ = "pgn",
__append__ = True


def wrap (string, length):
    lines = []
    last = 0
    while True:
        if len(string)-last <= length:
            lines.append(string[last:])
            break
        i = string[last:length+last].rfind(" ")
        lines.append(string[last:i+last])
        last += i + 1
    return "\n".join(lines)

def save (file, model):
    
    status = reprResult[model.status]
    
    print >> file, '[Event "%s"]' % model.tags["Event"]
    print >> file, '[Site "%s"]' % model.tags["Site"]
    print >> file, '[Round "%d"]' % model.tags["Round"]
    print >> file, '[Date "%04d.%02d.%02d"]' % \
            (model.tags["Year"], model.tags["Month"], model.tags["Day"])
    print >> file, '[White "%s"]' % repr(model.players[WHITE])
    print >> file, '[Black "%s"]' % repr(model.players[BLACK])
    print >> file, '[Result "%s"]' % status

    if issubclass(model.variant, FischerRandomChess):
        print >> file, '[Variant "Fischerandom"]'
    
    if model.boards[0].asFen() != FEN_START:
        print >> file, '[SetUp "1"]'
        print >> file, '[FEN "%s"]' % model.boards[0].asFen()
    
    print >> file
    
    result = []
    sanmvs = listToSan(model.boards[0], model.moves)
    for i in range(0, len(sanmvs)):
        ply = i + model.lowply
        if ply % 2 == 0:
            result.append("%d." % (ply/2+1))
        elif i == 0:
            result.append("%d..." % (ply/2+1))
        result.append(sanmvs[i])
    result = " ".join(result)
    result = wrap(result, 80)
    
    print >> file, result, status
    file.close()


tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+\"(.+?)\"\]")

# token categories
COMMENT_REST, COMMENT_BRACE, COMMENT_NAG, \
VARIATION_START, VARIATION_END, \
RESULT, FULL_MOVE, MOVE_COUNT, MOVE, MOVE_COMMENT = range(1,11)

pattern = re.compile(r"""
    (\;.*?[\n\r])        # comment, rest of line style
    |(\{.*?\})           # comment, between {} 
    |(\$[0-9]+)          # comment, Numeric Annotation Glyph
    |(\()                # variation start
    |(\))                # variation end
    |(\*|1-0|0-1|1/2)    # result (spec requires 1/2-1/2 for draw, but we want to tolerate simple 1/2 too)
    |(([0-9]{1,3}[.]+\s*)*([a-hxOoKQRBN0-8+#=-]{2,7})([\?!]{1,2})*)    # move (full, count, move with ?!, ?!)
    """, re.VERBOSE | re.DOTALL)


def load (file):
    files = []
    inTags = False
    
    for line in file:
        line = line.lstrip()
        if not line: continue
        elif line.startswith("%"): continue
        
        if line.startswith("["):
            if not inTags:
                files.append(["",""])
                inTags = True
            files[-1][0] += line
        
        else:
            inTags = False
            if not files:
                # In rare cases there might not be any tags at all. It's not
                # legal, but we support it anyways.
                files.append(["",""])
            files[-1][1] += line
    
    return PGNFile (files)


def parse_string(string, model, position, parent=None, variation=False):
    nodes = []

    node = Node()
    node.parent = parent
    last_node = node
    nodes.append(node)

    error = None
    parenthesis = 0
    v_string = ""
    for i, m in enumerate(re.finditer(pattern, string)):
        group, text = m.lastindex, m.group(m.lastindex)
        if parenthesis > 0:
            v_string += ' '+text

        if group == VARIATION_END:
            parenthesis -= 1
            if parenthesis == 0:
                v_last_node.variations.append(parse_string(v_string[:-1], model, position, v_parent, True))
                v_string = ""
                continue

        elif group == VARIATION_START:
            parenthesis += 1
            if parenthesis == 1:
                v_parent = node
                v_last_node = last_node

        if parenthesis == 0:
            if group == FULL_MOVE:
                if parenthesis == 0:
                    node = Node()
                    mstr = m.group(MOVE)
                    node.move = mstr

                    if m.group(MOVE_COMMENT):
                        node.move += m.group(MOVE_COMMENT)

                    if last_node:
                        node.previous = last_node
                        last_node.next = node
                    nodes.append(node)
                    last_node = node

                    if not variation:
                        if position != -1 and model.ply >= position:
                            break

                        try:
                            move = parseAny (model.boards[-1], mstr)
                        except ParsingError, e:
                            notation, reason, boardfen = e.args
                            ply = model.boards[-1].ply
                            if ply % 2 == 0:
                                moveno = "%d." % (i/2+1)
                            else: moveno = "%d..." % (i/2+1)
                            errstr1 = _("The game can't be read to end, because of an error parsing move %s '%s'.") % (moveno, notation)
                            errstr2 = _("The move failed because %s.") % reason
                            error = LoadingError (errstr1, errstr2)
                            break

                        model.moves.append(move)
                        model.boards.append(model.boards[-1].move(move))
                        node.board = model.boards[-1] 
                    
                        # This is for the sidepanels
                        model.emit("game_changed")

            elif group == COMMENT_REST:
                # TODO: comments have to be a list
                last_node.comments.append(text)

            elif group == COMMENT_BRACE:
                if node.parent is None and node.previous is None:
                    model.comment = text
                else:
                    last_node.comments.append(text)

            elif group == COMMENT_NAG:
                node.move += ' ' + nag_replace(text)

            elif group == RESULT:
                if text == "1/2":
                    model.status = reprResult.index("1/2-1/2")
                else:
                    model.status = reprResult.index(text)
                break

            else:
                print "Unknown:",text

        if error:
            raise error

    return nodes


class PGNFile (ChessFile):
    
    def __init__ (self, games):
        ChessFile.__init__(self, games)
        self.expect = None
        self.tagcache = {}
    
    def loadToModel (self, gameno, position, model=None):
        if not model:
            model = GameModel()

        fenstr = self._getTag(gameno, "FEN")
        variant = self._getTag(gameno, "Variant")
        if variant and ("fischer" in variant.lower() or "960" in variant):
            from pychess.Variants.fischerandom import FRCBoard
            model.variant = FischerRandomChess
            model.boards = [FRCBoard(fenstr)]
        else:
            if fenstr:
                model.boards = [Board(fenstr)]
            else:
                model.boards = [Board(setup=True)]

        del model.moves[:]
        model.status = WAITING_TO_START
        model.reason = UNKNOWN_REASON
        
        model.notation_string = self.games[gameno][1]
        model.nodes = parse_string(model.notation_string, model, position)

        if model.timemodel:
            blacks = len(model.moves)/2
            whites = len(model.moves)-blacks
            model.timemodel.intervals = [
                [model.timemodel.intervals[0][0]]*(whites+1),
                [model.timemodel.intervals[1][0]]*(blacks+1),
            ]
            log.debug("intervals %s" % model.timemodel.intervals)
        
        if model.status == WAITING_TO_START:
            model.status, model.reason = getStatus(model.boards[-1])
        
        return model
    
    def _getTag (self, gameno, tagkey):
        if gameno in self.tagcache:
            if tagkey in self.tagcache[gameno]:
                return self.tagcache[gameno][tagkey]
            else: return None
        else:
            if self.games:
                self.tagcache[gameno] = dict(tagre.findall(self.games[gameno][0]))
                return self._getTag(gameno, tagkey)
            else:
                return None
    
    def get_player_names (self, no):
        p1 = self._getTag(no,"White") and self._getTag(no,"White") or "Unknown"
        p2 = self._getTag(no,"Black") and self._getTag(no,"Black") or "Unknown"
        return (p1, p2)
    
    def get_elo (self, no):
        p1 = self._getTag(no,"WhiteElo") and self._getTag(no,"WhiteElo") or "1600"
        p2 = self._getTag(no,"BlackElo") and self._getTag(no,"BlackElo") or "1600"
        p1 = p1.isdigit() and int(p1) or 1600
        p2 = p2.isdigit() and int(p2) or 1600
        return (p1, p2)
    
    def get_date (self, no):
        date = self._getTag(no,"Date")
        today = datetime.date.today()
        if not date:
            return today.timetuple()[:3]
        return [ s.isdigit() and int(s) or today.timetuple()[i] \
                 for i,s in enumerate(date.split(".")) ]
    
    def get_site (self, no):
        return self._getTag(no,"Site") and self._getTag(no,"Site") or "?"
    
    def get_event (self, no):
        return self._getTag(no,"Event") and self._getTag(no,"Event") or "?"
    
    def get_round (self, no):
        round = self._getTag(no,"Round")
        if not round: return 1
        if round.find(".") >= 1:
            round = round[:round.find(".")]
        if not round.isdigit(): return 1
        return int(round)
        
    def get_result (self, no):
        pgn2Const = {"*":RUNNING, "1/2-1/2":DRAW, "1/2":DRAW, "1-0":WHITEWON, "0-1":BLACKWON}
        if self._getTag(no,"Result") in pgn2Const:
            return pgn2Const[self._getTag(no,"Result")]
        return RUNNING


class Node:
    def __init__(self):
        self.move = ""    # algebraic notation of the move
        self.comments = []
        self.annotations = []
        self.board = None
        self.variations = []
        self.parent = None
        self.next = None
        self.previous = None
    
    def __repr__(self):
        x = self.move
        for v in self.variations:
            print '-',v,'-'
            x += repr(v)
        return x


def nag_replace(nag):
    if nag == "$0": return ""
    elif nag == "$1": return "!"
    elif nag == "$2": return "?"
    elif nag == "$3": return "!!"
    elif nag == "$4": return "??"
    elif nag == "$5": return "!?"
    elif nag == "$6": return "?!"
    elif nag == "$11": return "="
    elif nag == "$14": return "+="
    elif nag == "$15": return "=+"
    elif nag == "$16": return "+/-"
    elif nag == "$17": return "-/+"
    elif nag == "$18": return "+-"
    elif nag == "$19": return "-+"
    elif nag == "$20": return "+--"
    elif nag == "$21": return "--+"
    else: return nag
    