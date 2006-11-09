from Utils.History import hisPool
from Utils.Move import Move, movePool
from Utils.Cord import Cord
from System.Log import log
from Utils.const import *
from time import time

range8 = range(8)

def validate (move, board, testCheck=True):
    """Will asume the first cord is an ally piece"""
    
    piece = board[move.cord0]
    
    if not piece:
        return False
    
    if piece.sign == PAWN:
        if not Pawn(move, board):
            return False
    elif piece.sign == KNIGHT:
        if not Knight(move, board):
           return False
    elif piece.sign == BISHOP:
        if not Bishop(move, board):
            return False
    elif piece.sign == ROOK:
        if not Rook(move, board):
            return False
    elif piece.sign == QUEEN:
        if not Queen(move, board):
            return False
    elif piece.sign == KING:
        if not King(move, board):
            return False
    
    if testCheck:
        if willCheck(board, move):
            return False
    
    return True
    
def Bishop (move, board):
    if abs(move.cord0.x - move.cord1.x) != abs(move.cord0.y - move.cord1.y):
        return False
    dx = move.cord1.x > move.cord0.x and 1 or -1
    dy = move.cord1.y > move.cord0.y and 1 or -1
    x = move.cord0.x
    y = move.cord0.y
    for i in range8:
        x += dx; y += dy
        if x == move.cord1.x or y == move.cord0.y:
            break
        if board.data[y][x] != None:
            return False
    return True

def genBishop (cord, board):
    for dx, dy in (1,1),(-1,1),(-1,-1),(1,-1):
        x, y = cord.x, cord.y
        while True:
            x += dx
            y += dy
            if not (0 <= x <= 7 and 0 <= y <= 7):
                break
            if board.data[y][x]:
                if board.data[y][x].color == board.color:
                    break
                else:
                    yield x,y
                    break
            yield x,y

def _isclear (board, cols, rows):
    for row in rows:
        for col in cols:
            if board.data[row][col] != None:
                return False
    return True

moveToCastling = {"e1g1": WHITE_OO, "e1c1": WHITE_OOO,
                  "e8g8": BLACK_OO, "e8c8": BLACK_OOO}
def King (move, board):

    strmove = str(move)
    if strmove in moveToCastling:
        if not board.castling & moveToCastling[strmove]:
            return False
        
        rows = board.color == BLACK and (7,) or (0,)
        if move.cord0.x < move.cord1.x:
            cols = [5,6]
            rookx = 7
        else:
            cols = [1,2,3]
            rookx = 0
        
        if board.data[rows[0]][rookx] == None:
            return False
        
        if not _isclear(board, cols, rows):
            return False
        
        cols.append(4)
        opcolor = 1 - board.color
        if genMovesPointingAt (board, cols, rows, opcolor):
            return False
        
        return True

    return abs(move.cord0.x - move.cord1.x) <= 1 and \
           abs(move.cord0.y - move.cord1.y) <= 1

kingPlaces = (1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1),(0,1),(1,1)
def genKing (cord, board):
    for dx, dy in kingPlaces:
        x, y = cord.x+dx, cord.y+dy
        if not (0 <= x <= 7 and 0 <= y <= 7):
            continue
        if not board.data[y][x] or board.data[y][x].color != board.color:
            yield x,y
            
    if board.color == WHITE:
        if board.castling & WHITE_OO and board.data[0][7] != None:
            if _isclear (board, (5,6), (0,)) and \
               not genMovesPointingAt (board, (4,5), (0,), BLACK):
                yield 6,0
        if board.castling & WHITE_OOO and board.data[0][0] != None:
            if _isclear (board, (1,2,3), (0,)) and \
               not genMovesPointingAt (board, (3,4), (0,), BLACK):
                yield 2,0
    if board.color == BLACK:
        if board.castling & BLACK_OO and board.data[7][7] != None:
            if _isclear (board, (5,6), (7,)) and \
               not genMovesPointingAt (board, (4,5), (7,), WHITE):
                yield 6,7
        if board.castling & BLACK_OOO and board.data[7][0] != None:
            if _isclear (board, (1,2,3), (7,)) and \
               not genMovesPointingAt (board, (3,4), (7,), WHITE):
                yield 2,7

def Knight (move, board):
    return (abs(move.cord0.x - move.cord1.x) == 1 and \
            abs(move.cord0.y - move.cord1.y) == 2) or \
           (abs(move.cord0.x - move.cord1.x) == 2 and \
            abs(move.cord0.y - move.cord1.y) == 1)

knightPlaces = (1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)
def genKnight (cord, board):
    for dx, dy in knightPlaces:
        x, y = cord.x+dx, cord.y+dy
        if not (0 <= x <= 7 and 0 <= y <= 7):
            continue
        if not board.data[y][x] or board.data[y][x].color != board.color:
            yield x,y

def Pawn (move, board):
    dr = board.color == WHITE and 1 or -1
    #Leaves only 1 and 2 cords difference - ahead
    if not 0 < (move.cord1.y - move.cord0.y)*dr <= 2:
        return False
    #Handles normal move
    if (move.cord1.y - move.cord0.y)*dr == 1 and \
        move.cord0.x == move.cord1.x and \
        board[move.cord1] == None:
        return True
    #Handles capturing
    if (move.cord1.y - move.cord0.y)*dr == 1 and \
        abs(move.cord0.x - move.cord1.x) == 1:
        #Normal
        if board[move.cord1] != None and \
           board[move.cord1].color != board.color:
            return True
        #En passant
        if board.enpassant == move.cord1:
        	return True
    #Handles double move
    row = board.color == WHITE and 1 or 6
    if (move.cord1.y - move.cord0.y)*dr == 2 and \
        move.cord0.y == row and \
        board[move.cord1] == None and \
        board[Cord(move.cord0.x, move.cord0.y+dr)] == None and \
        move.cord0.x == move.cord1.x:
        return True
    return False

def genPawn (cord, board):

    direction = board.color == WHITE and 1 or -1
    x, y = cord.x, cord.y
    if not board.data[y+direction][x]:
        yield x, y+direction
        
    row = board.color == WHITE and 1 or 6
    if y == row:
        if not board.data[y+direction*2][x] and \
           not board.data[y+direction][x]:
            yield x, y+direction*2
    
    for side in (1,-1):
        if not 0 <= x+side <= 7: continue
        if board.data[y+direction][x+side] and \
           board.data[y+direction][x+side].color != board.color:
            yield x+side, y+direction
    
    if board.enpassant and abs(board.enpassant.x - cord.x) == 1:
        if (board.enpassant.y == 5 and board.color == WHITE and cord.y == 4) or \
           (board.enpassant.y == 2 and board.color == BLACK and cord.y == 3) :
            yield board.enpassant.x, board.enpassant.y
     
def Rook (move, board):
    if move.cord0.x != move.cord1.x and move.cord0.y != move.cord1.y:
        return False
    
    if move.cord1.x > move.cord0.x:
        dx = 1; dy = 0
    elif move.cord1.x < move.cord0.x:
        dx = -1; dy = 0
    elif move.cord1.y > move.cord0.y:
        dx = 0; dy = 1
    elif move.cord1.y < move.cord0.y:
        dx = 0; dy = -1
    x = move.cord0.x
    y = move.cord0.y
    
    for i in range8:
        x += dx; y += dy
        if x == move.cord1.x and y == move.cord1.y:
            break
        if board.data[y][x] != None:
            return False
    return True

def genRook (cord, board):
    for dx, dy in (1,0),(0,-1),(-1,0),(0,1):
        x, y = cord.x, cord.y
        while True:
            x += dx
            y += dy
            if not (0 <= x <= 7 and 0 <= y <= 7):
                break
            if board.data[y][x]:
                if board.data[y][x].color == board.color:
                    break
                else:
                    yield x,y
                    break
            yield x,y

def Queen (move, board):
    return Rook (move, board) or \
           Bishop (move, board)

def genQueen (cord, board):
    for move in genRook (cord, board):
        yield move
    for move in genBishop (cord, board):
        yield move

sign2gen = [genKing, genQueen, genRook, genBishop, genKnight, genPawn]

def findMoves2 (board, testCheck=True):
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if not piece: continue
            if piece.color != board.color: continue
            cord0 = Cord(x,y)
            for xy in sign2gen[piece.sign](cord0,board):
                move = movePool.pop(cord0, Cord(*xy))
                try:
                    if not testCheck or not willCheck(board, move):
                        yield move
                    else: movePool.add(move)
                except Exception:
                    print piece, cord0, "\n", board
                    raise

def _getLegalMoves (board, cord, testCheck):
    cords = []
    for row in range8:
        for col in range8:
            if row == cord.y and col == cord.x: continue
            if abs(row - cord.y) <= 2 or abs(col - cord.x) <= 2 or \
                    cord.y == row or cord.x == col or \
                    abs(cord.y - row) == abs(cord.x - col):
                cord1 = Cord(col, row)
                move = movePool.pop(cord, cord1)
                if validate (move, board, testCheck):
                    cords.append(cord1)
                movePool.add(move)
    return cords

def findMoves (board):
    #t = time()
    
    moves = {}
    for move in findMoves2(board, True):
        c0, c1 = move.cords
        if c0 in moves:
            moves[c0].append(c1)
        else: moves[c0] = [c1]
    
    #board = history[-1]
    #color = history.curCol()
    #for y, row in enumerate(board.data):
    #    for x, piece in enumerate(row):
    #        if not piece: continue
    #        if piece.color != color: continue
    #        cord0 = Cord(x, y)
    #        for cord1 in _getLegalMoves (history, cord0, True):
    #            if cord0 in moves:
    #                moves[cord0].append(cord1)
    #            else: moves[cord0] = [cord1]
                
    #mvcount = sum([len(v) for v in moves.values()])
    #log.log("Found %d moves in %.3f seconds\n" % (mvcount, time()-t))
    #log.debug(str(moves))
    
    return moves

def getMovePointingAt (board, cord, color=None, sign=None, r=None, c=None):

    if board.movelist != None:
        for cord0, cord1s in board.movelist.iteritems():
            piece = board[cord0]
            if color != None and piece.color != color: continue
            if sign != None and piece.sign != sign: continue
            if r != None and cord0.y != r: continue
            if c != None and cord0.x != c: continue
            for cord1 in cord1s:
                if cord1 == cord:
                    return cord0
    
    else:
        cords = []
        for y, row in enumerate(board.data):
            for x, piece in enumerate(row):
                if piece == None: continue
                if color != None and piece.color != color: continue
                if sign != None and piece.sign != sign: continue
                if r != None and y != r: continue
                if c != None and x != c: continue
                cord1 = Cord(x,y)
                moves = _getLegalMoves(board,cord1,False)
                if cord in moves:
                    cords.append(cord1)
        
        if len(cords) == 1:
            return cords[0]
        
        # If there are more than one piece that can be moved to the cord,
        # We have to test if one of them moving will cause check.
        elif len(cords) > 1:
            print "cord", cord, "cords", cords
            for cord1 in cords:
            	move = movePool.pop(cord, cord1)
            	if willCheck(board,move):
            	    return cord1
            	else: movePool.add(move)
            
        else: return None

def genMovesPointingAt (board, cols, rows, color, testCheck=False):
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if piece == None: continue
            if piece.color != color: continue
            cord0 = Cord(x,y)
            for r in rows:
                for c in cols:
                    move = movePool.pop(cord0, Cord(c,r))
                    if validate (move, board, testCheck):
                        return move
                    movePool.add(move)

def willCheck (board, move):
    board2 = board.move(move)
    check = isCheck(board2, board.color)
    return check

from System.LimitedDict import LimitedDict
checkDic = LimitedDict(5000)

def isCheck (board, who):  
    
    if board in checkDic:
        r = checkDic[board][who]
        if r != None:
            return r
    
    cord = _findKing(board, who)
    if genMovesPointingAt(board, (cord.x,), (cord.y,), 1-who):
        r = True
    else: r = False
    
    if not board in checkDic:
        checkDic[board] = [None,None]
    checkDic[board][who] = r
    
    return r

def _findKing (board, color):
    for x in range8:
        for y in range8:
            piece = board.data[y][x]
            if piece and piece.sign == KING and piece.color == color:
                return Cord(x,y)
    raise Exception, "Could not find %s king on board ?!\n%s" % \
            (reprColor[color], repr(board))

def status (history):

	# FIXME: We don't test enough to know if positions are equal to the FIDE rules:
	# Positions are not the same if:
	# * a pawn that could have been captured,
	# * en passant can no longer be captured
	# * the right to castle has been changed.

    if len(history) >= 9 and history[-1] == history[-5] == history[-9]:
        return DRAW, DRAW_REPITITION
    
    board = history[-1]
    
    if board.fifty >= 100:
        return DRAW, DRAW_50MOVES
    
    if len(board.movelist) == 0:
        if isCheck(board, board.color):
            if board.color == WHITE:
                return BLACKWON, WON_MATE
            else: return WHITEWON, WON_MATE
            
        return DRAW, DRAW_STALEMATE
        
    return RUNNING, None
