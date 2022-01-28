class card:
    def __init__(self, id, value, color):
        self.id = id
        self.value = value
        self.color = color

hand = [card(0,1,'red'),card(0,1,'blue'),card(0,4,'red'),card(0,0,0),card(0,0,0)]

state = { 'tableCards': {
          'red': [card(0,1,'red'),card(0,2,'red')],
          'blue': [card(0,1,'blue')],
          'yellow': [],
          'green': [],
          'white': [],
          }
    }

def checkPlayableCard(state,playerHand): # check if there is a known n+1 card in hand wrt the same color n card on table
    for c in playerHand:
        if c.value==0:
            continue
        if c.color==None:
            continue
        if max([i.value for i in state['tableCards'][c.color]]) == (c.value-1):
            return True
    return False

class card:
    def __init__(self, id, value, color):
        self.id = id
        self.value = value
        self.color = color

hand = [card(0,0,None),card(0,0,None),card(0,0,None),card(0,0,None),card(0,0,None)]
steohand = [card(0,2,'white'),card(0,2,'green'),card(0,5,'green'),card(0,4,'red'),card(0,2,'yellow')]

tableCards = {
          'red': [card(0,1,'red'),card(0,2,'red')],
          'blue': [card(0,1,'blue')],
          'yellow': [],
          'green': [card(0,1,'green'),card(0,2,'green')],
          'white': [],
          }
    
class player:
    def __init__(self, name, hand):
        self.name = name
        self.hand = hand
        
players = [ player('albo',[]), player('steo',steohand) ]

discardPile = [ card(0,1,'red'), card(0,1,'white'), card(0,5,'white') ]

class state:
    def __init__(self, tableCards, players, discardPile, currentPlayer, usedNoteTokens, usedStormTokens):
        self.tableCards=tableCards
        self.players=players
        self.discardPile=discardPile
        self.currentPlayer=currentPlayer
        self.usedNoteTokens=usedNoteTokens
        self.usedStormTokens=usedStormTokens
        
act_state = state(tableCards,players,discardPile, 'albo', 0, 0)

def checkPlayedOne(state,playerHand): # check if there is a known 1 card that has never been played
    for c in playerHand:
        if c.value==1:
            if c.color==None:
                continue
            if len(state.tableCards[c.color])==0:
                return True
    return False

def checkPlayableCard(state,playerHand): # check if there is a known n+1 card in hand wrt the same color n card on table
    for c in playerHand:
        if c.value==0:
            continue
        if c.color==None:
            continue
        if max([i.value for i in state.tableCards[c.color]],default=0) == (c.value-1):
            return True
    return False

def checkFoldableCard(state,playerHand,player): # check if there is a foldable card

    notInDiscardPile = []

    for c in playerHand:
        
        if c.value==0:
            continue
        if c.color==None:
            continue

        chk = True
        for d in state.discardPile:
            if c.value==d.value and c.color==d.color:
                chk = False
                break
        if chk:
            notInDiscardPile.append(c)

    if len(notInDiscardPile)==0:
        return False

    for c in notInDiscardPile:
        #dupCheck is a list to check if c has duplicate in hand
        dupCheck = [i for i in notInDiscardPile if i.value==c.value and i.color==c.color]
        if len(dupCheck)==2:
            return True

        #check if another player has the same card
        for p in state.players:
            if p.name == player:
                continue
            for d in p.hand: #each card in player p hand
                if d.value==c.value and d.color==c.color:
                    return True

        #check if card has been already played
        if max([i.value for i in state.tableCards[c.color]],default=0)>=c.value:
            return True

    return False

def checkPlayerHasPlayable(state): #check if any player has a playable card
    for p in state.players:
        if checkPlayableCard(state,p.hand):
            return True
    return False

def checkPlayerHasFoldable(state): #check if any player has a foldable card
    for p in state.players:
        if checkFoldableCard(state,p.hand,p.name):
            return True
    return False

def checkRemainingHints(state): #check remaining hint tokens
    if state.usedNoteTokens==0:
        return True,True
    elif state.usedNoteTokens<4:
        return True,False
    elif state.usedNoteTokens<7:
        return False,True
    else:
        return False,False

def checkStormTokens(state): #check how many errors
    if state.usedStormTokens<2:
        return False
    else:
        return True

def getQrow(state,playerHand): #gives an integer corresponding to the T-table row
    checks = [ checkPlayedOne(state,playerHand), checkPlayableCard(state,playerHand), 
               checkFoldableCard(state,playerHand,state.currentPlayer), checkPlayerHasPlayable(state),
               checkPlayerHasFoldable(state), checkStormTokens(state) ] + [i for i in checkRemainingHints(state)]
    return sum([checks[i]*(2**i) for i in range(8)])

print(getQrow(act_state, hand))
