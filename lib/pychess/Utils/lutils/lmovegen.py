from __future__ import absolute_import

from .bitboard import *
from .attack import *
from pychess.Utils.const import *

################################################################################
#   The format of a move is as follows - from left:                            #
#   4 bits:  Descriping the type of the move                                   #
#   6 bits:  cord to move from                                                 #
#   6 bits:  cord to move to                                                   #
################################################################################

shiftedFromCords = []
for i in range(64):
    shiftedFromCords.append(i << 6)

shiftedFlags = []
for i in NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, ENPASSANT, \
            KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION, KING_PROMOTION, NULL_MOVE, DROP:
    shiftedFlags.append(i << 12)

def newMove (fromcord, tocord, flag=NORMAL_MOVE):
    return shiftedFlags[flag] + shiftedFromCords[fromcord] + tocord

################################################################################
#   Generate all moves                                                         #
################################################################################

def genCastles (board):
    def generateOne (color, side, king_after, rook_after):
        if side == 0:
            castle = QUEEN_CASTLE
        else:
            castle = KING_CASTLE
        king = board.ini_kings[color]
        rook = board.ini_rooks[color][side]
        blocker = clearBit(clearBit(board.blocker, king), rook)
        stepover = fromToRay[king][king_after] | fromToRay[rook][rook_after]
        if not stepover & blocker:
            for cord in range(min(king,king_after), max(king,king_after)+1):
                if isAttacked (board, cord, 1-color):
                    return
            if FILE(king) == 3 and board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
                castle = QUEEN_CASTLE if castle == KING_CASTLE else KING_CASTLE
            return newMove (king, king_after, castle)
    
    king = board.ini_kings[board.color]
    wildcastle = FILE(king) == 3 and board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS)
    if board.color == WHITE:
        if board.castling & W_OO:
            side = 0 if wildcastle else 1
            move = generateOne (WHITE, side, board.fin_kings[WHITE][side], board.fin_rooks[WHITE][side]) 
            if move: yield move
        
        if board.castling & W_OOO:
            side = 1 if wildcastle else 0
            move = generateOne (WHITE, side, board.fin_kings[WHITE][side], board.fin_rooks[WHITE][side]) 
            if move: yield move
    else:
        if board.castling & B_OO:
            side = 0 if wildcastle else 1
            move = generateOne (BLACK, side, board.fin_kings[BLACK][side], board.fin_rooks[BLACK][side]) 
            if move: yield move
        
        if board.castling & B_OOO:
            side = 1 if wildcastle else 0
            move = generateOne (BLACK, side, board.fin_kings[BLACK][side], board.fin_rooks[BLACK][side]) 
            if move: yield move

def genPieceMoves(board, piece, tcord):
    """"
    Used by parseSAN only to accelerate it a bit
    """
    moves = set()
    friends = board.friends[board.color]
    notfriends = ~friends
    if piece == KNIGHT:
        knights = board.boards[board.color][KNIGHT]
        knightMoves = moveArray[KNIGHT]
        for fcord in iterBits(knights):
            if tcord in iterBits(knightMoves[fcord] & notfriends):
                moves.add(newMove(fcord, tcord))
        return moves
        
    if piece == BISHOP:
        blocker = board.blocker
        bishops = board.boards[board.color][BISHOP]
        for fcord in iterBits(bishops):
            attackBoard = attack45 [fcord][ray45 [fcord] & blocker] | \
                          attack135[fcord][ray135[fcord] & blocker]
            if tcord in iterBits(attackBoard & notfriends):
                moves.add(newMove(fcord, tcord))
        return moves
        
    if piece == ROOK:
        blocker = board.blocker
        rooks = board.boards[board.color][ROOK]
        for fcord in iterBits(rooks):
            attackBoard = attack00[fcord][ray00[fcord] & blocker] | \
                          attack90[fcord][ray90[fcord] & blocker]
            if tcord in iterBits(attackBoard & notfriends):
                moves.add(newMove(fcord, tcord))
        return moves

    if piece == QUEEN:
        blocker = board.blocker
        queens = board.boards[board.color][QUEEN]
        for fcord in iterBits(queens):
            attackBoard = attack45 [fcord][ray45 [fcord] & blocker] | \
                          attack135[fcord][ray135[fcord] & blocker]
            if tcord in iterBits(attackBoard & notfriends):
                moves.add(newMove(fcord, tcord))

            attackBoard = attack00[fcord][ray00[fcord] & blocker] | \
                          attack90[fcord][ray90[fcord] & blocker]
            if tcord in iterBits(attackBoard & notfriends):
                moves.add(newMove(fcord, tcord))
        return moves
        
    if board.variant == SUICIDECHESS and piece == KING:
        kings = board.boards[board.color][KING]
        if kings:
            kingMoves = moveArray[KING]
            for fcord in iterBits(kings):
                for tcord in iterBits(kingMoves[fcord] & notfriends):
                    moves.add(newMove(fcord, tcord))
            return moves

def genAllMoves (board, drops=True):
    
    blocker = board.blocker
    notblocker = ~blocker
    enpassant = board.enpassant
    
    friends = board.friends[board.color]
    notfriends = ~friends
    enemies = board.friends[1- board.color]
    
    pawns = board.boards[board.color][PAWN]
    knights = board.boards[board.color][KNIGHT]
    bishops = board.boards[board.color][BISHOP]
    rooks = board.boards[board.color][ROOK]
    queens = board.boards[board.color][QUEEN]
    kings = board.boards[board.color][KING]
    
    # Knights
    knightMoves = moveArray[KNIGHT]
    for cord in iterBits(knights):
        for c in iterBits(knightMoves[cord] & notfriends):
            yield newMove(cord, c)
    
    # King
    if kings:
        kingMoves = moveArray[KING]
        cord = firstBit( kings )
        for c in iterBits(kingMoves[cord] & notfriends):
            if board.variant == ATOMICCHESS:
                if not board.arBoard[c]:
                    yield newMove(cord, c)
            else:
                yield newMove(cord, c)
    
    # Rooks and Queens
    for cord in iterBits(rooks | queens):
        attackBoard = attack00[cord][ray00[cord] & blocker] | \
                      attack90[cord][ray90[cord] & blocker]
        for c in iterBits(attackBoard & notfriends):
            yield newMove(cord, c)
    
    # Bishops and Queens
    for cord in iterBits(bishops | queens):
        attackBoard = attack45 [cord][ray45 [cord] & blocker] | \
                      attack135[cord][ray135[cord] & blocker]
        for c in iterBits(attackBoard & notfriends):
            yield newMove(cord, c)
    
    # White pawns
    pawnEnemies = enemies | (enpassant != None and bitPosArray[enpassant] or 0)
    if board.color == WHITE:
        
        # One step
        
        movedpawns = (pawns >> 8) & notblocker # Move all pawns one step forward
        for cord in iterBits(movedpawns):
            if cord >= 56:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord-8, cord, p)
            else:
                #if (cord-8, cord) == (33, 41):
                #    print repr(board)
                #print toString(pawns)
                yield newMove (cord-8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[1] # Get seccond row pawns
        movedpawns = (seccondrow >> 8) & notblocker # Move two steps forward, while
        movedpawns = (movedpawns >> 8) & notblocker # ensuring middle cord is clear
        for cord in iterBits(movedpawns):
            yield newMove (cord-16, cord)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord >= 56:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord-7, cord, p)
            elif cord == enpassant:
                yield newMove (cord-7, cord, ENPASSANT)
            else:
                yield newMove (cord-7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord >= 56:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord-9, cord, p)
            elif cord == enpassant:
                yield newMove (cord-9, cord, ENPASSANT)
            else:
                yield newMove (cord-9, cord)
    
    # Black pawns
    else:
        
        # One step
        
        movedpawns = (pawns << 8) & notblocker
        movedpawns &= 0xffffffffffffffff  # contrain to 64 bits
        for cord in iterBits(movedpawns):
            if cord <= 7:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord+8, cord, p)
            else:
                yield newMove (cord+8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[6] # Get seventh row pawns
        # Move two steps forward, while ensuring middle cord is clear
        movedpawns = seccondrow << 8 & notblocker
        movedpawns = movedpawns << 8 & notblocker
        for cord in iterBits(movedpawns):
            yield newMove (cord+16, cord)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = capLeftPawns << 7 & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord <= 7:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord+7, cord, p)
            elif cord == enpassant:
                yield newMove (cord+7, cord, ENPASSANT)
            else:
                yield newMove (cord+7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = capRightPawns << 9 & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord <= 7:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord+9, cord, p)
            elif cord == enpassant:
                yield newMove (cord+9, cord, ENPASSANT)
            else:
                yield newMove (cord+9, cord)
    
    # Castling
    if kings:
        for move in genCastles(board):
            yield move

    if drops and board.variant == CRAZYHOUSECHESS:
        for move in genDrops(board):
            yield move

################################################################################
#   Generate capturing moves                                                   #
################################################################################

def genCaptures (board):
    
    blocker = board.blocker
    notblocker = ~blocker
    enpassant = board.enpassant
    
    friends = board.friends[board.color]
    notfriends = ~friends
    enemies = board.friends[1- board.color]
    
    pawns = board.boards[board.color][PAWN]
    knights = board.boards[board.color][KNIGHT]
    bishops = board.boards[board.color][BISHOP]
    rooks = board.boards[board.color][ROOK]
    queens = board.boards[board.color][QUEEN]
    kings = board.boards[board.color][KING]
    
    # Knights
    knightMoves = moveArray[KNIGHT]
    for cord in iterBits(knights):
        for c in iterBits(knightMoves[cord] & enemies):
            yield newMove(cord, c)
    
    # King
    if kings:
        kingMoves = moveArray[KING]
        cord = firstBit( kings )
        for c in iterBits(kingMoves[cord] & enemies):
            if board.variant != ATOMICCHESS:
                yield newMove(cord, c)
    
    # Rooks and Queens
    for cord in iterBits(rooks|queens):
        attackBoard = attack00[cord][ray00[cord] & blocker] | \
                      attack90[cord][ray90[cord] & blocker]
        for c in iterBits(attackBoard & enemies):
            yield newMove(cord, c)
    
    # Bishops and Queens
    for cord in iterBits(bishops|queens):
        attackBoard = attack45 [cord][ray45 [cord] & blocker] | \
                      attack135[cord][ray135[cord] & blocker]
        for c in iterBits(attackBoard & enemies):
            yield newMove(cord, c)
    
    # White pawns
    pawnEnemies = enemies | (enpassant != None and bitPosArray[enpassant] or 0)
    
    if board.color == WHITE:
        
        # Promotes
        
        movedpawns = (pawns >> 8) & notblocker & rankBits[7]
        #for cord in iterBits(movedpawns):
        #    for p in PROMOTIONS:
        #        if board.variant == SUICIDECHESS or p != KING_PROMOTION:
        #            yield newMove(cord-8, cord, p)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord >= 56:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord-7, cord, p)
            elif cord == enpassant:
                yield newMove (cord-7, cord, ENPASSANT)
            else:
                yield newMove (cord-7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord >= 56:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord-9, cord, p)
            elif cord == enpassant:
                yield newMove (cord-9, cord, ENPASSANT)
            else:
                yield newMove (cord-9, cord)
    
    # Black pawns
    else:
        
        # One step
        
        movedpawns = pawns << 8 & notblocker & rankBits[0]
        #for cord in iterBits(movedpawns):
        #    for p in PROMOTIONS:
        #        if board.variant == SUICIDECHESS or p != KING_PROMOTION:
        #            yield newMove(cord+8, cord, p)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = capLeftPawns << 7 & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord <= 7:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord+7, cord, p)
            elif cord == enpassant:
                yield newMove (cord+7, cord, ENPASSANT)
            else:
                yield newMove (cord+7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = capRightPawns << 9 & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord <= 7:
                for p in PROMOTIONS:
                    if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                        yield newMove(cord+9, cord, p)
            elif cord == enpassant:
                yield newMove (cord+9, cord, ENPASSANT)
            else:
                yield newMove (cord+9, cord)

################################################################################
#   Generate escapes from check                                                #
################################################################################

def genCheckEvasions (board):
    color = board.color
    opcolor = 1-color
    
    kcord = board.kings[color]
    kings = board.boards[color][KING]
    pawns = board.boards[color][PAWN]
    checkers = getAttacks (board, kcord, opcolor)
    
    arBoard = board.arBoard
    if bin(checkers).count("1") == 1:

        # Captures of checking pieces (except by king, which we will test later)
        chkcord = firstBit (checkers)
        b = getAttacks (board, chkcord, color) & ~kings
        for cord in iterBits(b):
            if not pinnedOnKing (board, cord, color):
                if arBoard[cord] == PAWN and \
                        (chkcord <= H1 or chkcord >= A8):
                    for p in PROMOTIONS:
                        if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                            yield newMove(cord, chkcord, p)
                else:
                    yield newMove (cord, chkcord)
        
        # Maybe enpassant can help
        if board.enpassant:
            ep = board.enpassant
            if ep + (color == WHITE and -8 or 8) == chkcord:
                bits = moveArray[color == WHITE and BPAWN or PAWN][ep] & pawns
                for cord in iterBits (bits):
                    if not pinnedOnKing (board, cord, color):
                        yield newMove (cord, ep, ENPASSANT)
        
        # Lets block/capture the checking piece
        if sliders[arBoard[chkcord]]:
            bits = clearBit(fromToRay[kcord][chkcord], chkcord)
            
            for cord in iterBits (bits):
                b = getAttacks (board, cord, color)
                b &= ~(kings | pawns)
                
                # Add in pawn advances
                if color == WHITE and cord > H2:
                    if bitPosArray[cord-8] & pawns:
                        b |= bitPosArray[cord-8]
                    if cord >> 3 == 3 and arBoard[cord-8] == EMPTY and \
                            bitPosArray[cord-16] & pawns:
                        b |= bitPosArray[cord-16]
                
                elif color == BLACK and cord < H7:
                    if bitPosArray[cord+8] & pawns:
                        b |= bitPosArray[cord+8]
                    if cord >> 3 == 4 and arBoard[cord+8] == EMPTY and \
                            bitPosArray[cord+16] & pawns:
                        b |= bitPosArray[cord+16]
                
                for fcord in iterBits (b):
                    # If the piece is blocking another attack, we cannot move it
                    if pinnedOnKing (board, fcord, color):
                        continue
                    if arBoard[fcord] == PAWN and (cord > H7 or cord < A2):
                        for p in PROMOTIONS:
                            if board.variant == SUICIDECHESS or p != KING_PROMOTION:
                                yield newMove(fcord, cord, p)
                    else:
                        yield newMove (fcord, cord)
                    
                if board.variant == CRAZYHOUSECHESS:
                    holding = board.holding[color]
                    for piece in holding:
                        if holding[piece] > 0:
                            if piece == PAWN:
                                if cord >= 56 or cord <= 7:
                                    continue
                            yield newMove (piece, cord, DROP)
    
    # If more than one checkers, move king to get out of check
    if checkers:
        escapes = moveArray[KING][kcord] & ~board.friends[color]
    else: escapes = 0
    
    for chkcord in iterBits (checkers):
        dir = directions[chkcord][kcord]
        if sliders[arBoard[chkcord]]:
            escapes &= ~rays[chkcord][dir]
            
    for cord in iterBits (escapes):
        if not isAttacked (board, cord, opcolor):
            yield newMove (kcord, cord)


def genDrops (board):
    color = board.color
    arBoard = board.arBoard
    holding = board.holding[color]
    for piece in holding:
        if holding[piece] > 0:
            for cord, elem in enumerate(arBoard):
                if elem == EMPTY:
                    if piece == PAWN:
                        if cord >= 56 or cord <= 7:
                            continue
                    yield newMove(piece, cord, DROP)
