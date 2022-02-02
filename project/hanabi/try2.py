import checks as ck
import numpy as np
import Qprocess as qp

class card:
    def __init__(self, id, value, color):
        self.id = id
        self.value = value
        self.color = color

albo_hand = [card(0,0,None),card(0,0,None),card(0,0,None),card(0,0,None),card(0,0,None)]
steo_hand = [card(0,1,'white'),card(0,5,'yellow'),card(0,1,'red'),card(0,2,'yellow'),card(0,2,'white')]
tableCards = {
          'red': [],
          'blue': [],
          'yellow': [card(0, 1, 'yellow')],
          'green': [],
          'white': [],
          }

discardPile = []

class player:
    def __init__(self, name, hand):
        self.name = name
        self.hand = hand

players = [ player('albo',[]), player('steo',steo_hand) ]
memory = [card(0, 1, 'white'), card(0, 5, None), card(0, 1, None), card(0, 0, None), card(0, 0, 'white')]

class state:
    def __init__(self, tableCards, players, discardPile, currentPlayer, usedNoteTokens, usedStormTokens):
        self.tableCards=tableCards
        self.players=players
        self.discardPile=discardPile
        self.currentPlayer=currentPlayer
        self.usedNoteTokens=usedNoteTokens
        self.usedStormTokens=usedStormTokens

act_state = state(tableCards,players,discardPile, 'albo', 4, 0)

print(ck.chooseCardToPlay(act_state, memory))



