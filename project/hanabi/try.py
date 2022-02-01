from tabnanny import check
import numpy as np
import random
import Qprocess as qp
import checks

class card:
    def __init__(self, id, value, color):
        self.id = id
        self.value = value
        self.color = color

hand = [card(0,2,'yellow'),card(0,0,None),card(0,0,None),card(0,0,None),card(0,0,None)]
steohand = [card(0,3,'yellow'),card(0,4,'white'),card(0,2,'green'),card(0,2,'red'),card(0,1,'blue')]

hand2 = [card(0,3,'yellow'),card(0,1,'yellow'),card(0,5,'blue'),card(0,4,'red'),card(0,3,'blue')]
steohand2 = [card(0,0,None),card(0,4,None),card(0,2,'green'),card(0,0,None),card(0,1,None)]

steohand3 = [card(0,3,'yellow'),card(0,4,'white'),card(0,2,'green'),card(0,2,'red'),card(0,5,'yellow')]
tableCards = {
          'red': [],
          'blue': [],
          'yellow': [],
          'green': [],
          'white': [],
          }
tableCards3 = {
'red': [],
'blue': [card(0,1,'blue')],
'yellow': [],
'green': [],
'white': [],
}
discardPile = [ card(0,1,'red'), card(0,1,'white'), card(0,5,'white') ]

class player:
    def __init__(self, name, hand):
        self.name = name
        self.hand = hand
        
players = [ player('albo',[]), player('steo',steohand) ]
players2 = [ player('albo',hand2), player('steo',[]) ]
players3 = [ player('albo',[]), player('steo',steohand3) ]

class state:
    def __init__(self, tableCards, players, discardPile, currentPlayer, usedNoteTokens, usedStormTokens):
        self.tableCards=tableCards
        self.players=players
        self.discardPile=discardPile
        self.currentPlayer=currentPlayer
        self.usedNoteTokens=usedNoteTokens
        self.usedStormTokens=usedStormTokens
        
act_state = state(tableCards,players,discardPile, 'albo', 0, 0)
act_state2 = state(tableCards, players2,discardPile, 'steo', 1, 0)
act_state3 = state(tableCards3, players3, discardPile, 'albo', 1, 0)

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

#print(getQrow(act_state, hand))

def chooseCardToPlay(state,playerHand): #return card index to play
    score = [0,0,0,0,0]
    for c in playerHand:
        if c.value!=0:
            for color in state.tableCards:
                if max([i.value for i in state.tableCards[color]],default=0) == (c.value-1):
                    score[playerHand.index(c)] += 1
                    if color==c.color:
                        score[playerHand.index(c)] += 5
        if c.color!=None:
            if len(state.tableCards[c.color])==0:
                score[playerHand.index(c)] += 1 
        for p in state.players:
            if p.name == state.currentPlayer:
                continue
            for d in p.hand: #each card in player p hand
                if d.value==c.value+1 and d.color==c.color:
                    score[playerHand.index(c)] += 1
        if c.value==1:
            score[playerHand.index(c)] += 1

    best = max(score)
    npscore = np.array(score)
    playable = np.where(npscore==best)[0].tolist()
    ind = random.randint(0,len(playable)-1)
    return playable[ind]

    
#print("Card to play - index: ", chooseCardToPlay(act_state,hand))

def chooseCardToHint(state,playerHand):
    scores = {}
    for i in state.players:
        if i.name==state.currentPlayer:
            continue
        numbs = {i:0 for i in list(set([c.value for c in i.hand])) }
        cols = {i:0 for i in list(set([c.color for c in i.hand])) } # takes any owned color and transforms in {color: 0}
        scores.update({i.name: {'numbers': numbs, 'colors': cols}})
    
    for p in state.players:
        for c in p.hand:
            if max([i.value for i in state.tableCards[c.color]],default=0) == (c.value-1):
                    scores[p.name]['numbers'][c.value] += 5
                    scores[p.name]['colors'][c.color] += 5
            for d in playerHand:
                if d.value==0 or d.color==None:
                    continue
                if c.color==d.color and (c.value==d.value-1 or c.value==d.value+1):
                    scores[p.name]['numbers'][c.value] += 1
                    scores[p.name]['colors'][c.color] += 1
                if c.color==d.color and c.value==d.value:
                    scores[p.name]['numbers'][c.value] += 5
                    scores[p.name]['colors'][c.color] += 5
            for q in state.players:
                if q.name==p.name:
                    continue
                for d in q.hand:
                    if d.value==0 or d.color==None:
                        continue
                    if c.color==d.color and (c.value==d.value-1 or c.value==d.vale+1):
                        scores[p.name]['numbers'][c.value] += 1
                        scores[p.name]['colors'][c.color] += 1
                    if c.color==d.color and c.value==d.value:
                        scores[p.name]['numbers'][c.value] += 5
                        scores[p.name]['colors'][c.color] += 5
            dist = c.value - max([i.value for i in state.tableCards[c.color]],default=0)
            if dist>0:
                scores[p.name]['numbers'][c.value] += dist
                scores[p.name]['colors'][c.color] += dist
            if c.value==1:
                scores[p.name]['numbers'][c.value] += 1
            if len(state.tableCards[c.color])>0:
                scores[p.name]['colors'][c.color] += 1
            dupCheck = [i for i in p.hand if i.value==c.value and i.color==c.color]
            if len(dupCheck)==2 or max([i.value for i in state.tableCards[c.color]],default=0) >= c.value or \
                                len([i for i in state.discardPile if i.color==c.color and i.value==c.value])>0:
                scores[p.name]['numbers'][c.value] += 10
                scores[p.name]['colors'][c.color] += 10
            if c.value == 5:
                scores[p.name]['numbers'][c.value] += 5

    max_n = {'player': None, 'value': 0, 'points': -1}
    max_c = {'player': None, 'color': None, 'points': -1}

    for s in scores:
        key_list=list(scores[s]['numbers'].keys()) #all numbers
        val_list=list(scores[s]['numbers'].values()) #all points
        hintable = np.where(np.array(val_list)==max(val_list))[0].tolist()
        ind = hintable[random.randint(0,len(hintable)-1)]
        if val_list[ind] > max_n['points']: # if better then last found
            max_n['player'] = p.name
            max_n['points'] = val_list[ind] #associated points
            max_n['value'] = key_list[ind] # extracted number

        key_list=list(scores[s]['colors'].keys()) #all colors
        val_list=list(scores[s]['colors'].values()) #all points
        hintable = np.where(np.array(val_list)==max(val_list))[0].tolist()
        ind = hintable[random.randint(0,len(hintable)-1)]
        if val_list[ind] > max_c['points']: # if better then last found
            max_c['player'] = p.name
            max_c['points'] = val_list[ind] #associated points
            max_c['color'] = key_list[ind] # extracted color

    if max_n['points']>max_c['points']:
        return max_n
    elif max_n['points']<max_c['points']:
        return max_c
    else:
        h1 = list(filter(lambda p: p.name == max_n['player'], state.players))[0].hand
        h2 = list(filter(lambda p: p.name == max_c['player'], state.players))[0].hand
        if len([i for i in h1 if i.value == max_n['value']]) > \
           len([i for i in h2 if i.color== max_c['color']]):
            return max_n
        elif len([i for i in h1 if i.value == max_n['value']]) < \
             len([i for i in h2 if i.color == max_c['color']]):
            return max_c
        elif random.randint(0,1):
            return max_n
    return max_c

#print("Cards to hint: ", chooseCardToHint(act_state, hand))

def chooseCardToDiscard(state, playerHand):
    score = [0,0,0,0,0]
    for c in playerHand:
        if c.value!=0 and c.color!=None:
            dupCheck = [i for i in playerHand if i.value==c.value and i.color==c.color]
            if (len(dupCheck) >= 2) or max([i.value for i in state.tableCards[c.color]], default=0) >= c.value:
                score[playerHand.index(c)] += 10
            if (len([i for i in state.discardPile if i.color==c.color and i.value==c.value]) >0):
                score[playerHand.index(c)] -= 10
            for p in state.players:
                chk = 0
                if (p.name == state.currentPlayer):
                    continue
                for d in p.hand:
                    if (d.value == c.value+1 and d.color == c.color): 
                        score[playerHand.index(c)] -= 1
                        chk += 1
                    if (d.value == c.value and d.color == c.color):
                        score[playerHand.index(c)] += 1
                        chk += 1
                if (chk > 1): #if both conditions above met, break the entire cycle
                    break
            for color in state.tableCards:
                if (max([i.value for i in state.tableCards[color]], default=0) == (c.value-1)):
                    score[playerHand.index(c)] -= 1
                    if (color == c.color):
                        score[playerHand.index(c)] -= 5
        if c.color != None:
            if (len(state.tableCards[c.color]) > 0):
                score[playerHand.index(c)] -= 1
        if c.value == 1:
            score[playerHand.index(c)] -= 1        
        if c.color!=None:
            if len(state.tableCards[c.color])==0:
                score[playerHand.index(c)] -= 1 
        if c.value==1:
            score[playerHand.index(c)] -= 1
        if c.value==5:
            score[playerHand.index(c)] -= 10

    best = max(score)
    npscore = np.array(score)
    playable = np.where(npscore==best)[0].tolist()
    ind = random.randint(0,len(playable)-1)
    return playable[ind]

#print("Card to discard - index: ", chooseCardToDiscard(act_state,hand))

#qp.QTableFrom0()
#print(qp.loadQTableFromFile('Q-table-0.npy'))

'''
while True:
    index = checks.getQrow(act_state, hand)
    #print(index)
    move1 = chooseCardToHint(act_state, hand)
    reward = 5
    move2 = chooseCardToPlay(act_state2, steohand2)
    nextIndex = checks.getQrow(act_state3, hand)
    qp.updateQTable(index, nextIndex, 1, reward, path='Q-table-0.npy')
    print(qp.loadQTableFromFile('Q-table-0.npy')[200])
'''

ex = [card(1,1,'red'),card(2,2,'red'),card(3,3,'red')]

print(card(1,1,'red') in ex)

c = card(1,1,'red')

print([i for i in ex if i.id==c.id])
print(c.id in [i.id for i in ex if i.id==c.id])