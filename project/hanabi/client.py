from importlib.resources import path
from sys import argv, stdout
from threading import Thread

import GameData
import socket
from constants import *
import os
import checks as ck
import Qprocess as qp
import game
import time
import select

if (len(argv) < 4):
    print("You need the player name to start the game.")
    playerName = "Test" # For debug
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])

statuses = ["Lobby", "Game", "GameHint"]
status = statuses[0]

move = -1   # move: 0, 1, 2 -> play, hint, discard
index = -1  # index of the row about Qtable

def manageInput():
    global status
    global index
    global move

    hint_memory = {}    # memory of hints to other players
    hands_memory = {}   # memory of other players

    memory = [ game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None) ] # known cards -> 5 card 
    requested_show = False  # if there isn't info about show, we have to wait to receive it

    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())  # show to activate for the first time s.recv
    requested_show = True

    Qtable = False
    while not Qtable:
        Qtable = qp.loadQTableFromFile(path='Q-table.npy')   # list of size (256,3)
    
    while True:
        data = s.recv(DATASIZE)

        if not data:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())  # send another show request
            requested_show = True
            continue
        
        data = GameData.GameData.deserialize(data)  # intercept the show response
        if type(data) is GameData.ServerHintData:   # check if data is a hint response
            print("Hint type: " + data.type)
            print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))
            if data.destination == playerName: #if hint is for us, update our memory
                for i in data.positions:
                    if data.type =='value':
                        memory[i].value = data.value
                    else:
                        memory[i].color = data.value
                print()
                print("Owned cards:")
                for i in memory:    # print our memory
                    print(i.toClientString())
                print()
            else:   # update hint_memory for the target player
                for i in data.positions:
                    if data.destination not in hint_memory:
                        hint_memory[data.destination] = []
                    if {data.type: data.value} not in hint_memory[data.destination]:
                        hint_memory[data.destination].append({data.type: data.value})
            print()
            print("[" + playerName + " - " + status + "]: ", end="")
            print()
        elif type(data) is GameData.ServerGameOver:     # if we have received a GameOver
            print()
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            return

        # check if it is our turn
        if type(data) is not GameData.ClientGetGameStateRequest:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            requested_show = True
            data = s.recv(DATASIZE)
            if not data:
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                requested_show = True
                continue
            data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerGameStateData:  # intercept the show response
            for p in data.players:      # check if p.name is a key of hint_memory
                if p.name not in hint_memory:
                    hint_memory[p.name] = []

            if hands_memory:    # update other players' hint memory
                for p in data.players:
                    if p.name != playerName:
                        for c in p.hand:
                            if c.id not in [i.id for i in hands_memory[p.name] if i.id==c.id]:
                                color_hints = [i for i in hint_memory[p.name] if list(i.keys())[0]=='color']
                                value_hints = [i for i in hint_memory[p.name] if list(i.keys())[0]=='value']
                                hint_memory[p.name] = list(filter(lambda x : x['color']!=c.color, color_hints))
                                hint_memory[p.name] = hint_memory[p.name] + list(filter(lambda x : x['value']!=c.value, value_hints))

            for p in data.players:  # update other players' hand knowledge
                if p.name != playerName:
                    hands_memory[p.name] = p.hand.copy()

            requested_show = False  # if it isn't our turn we continue to wait for a show response
            if data.currentPlayer != playerName:
                continue
            else:
                print("show")
                print("Current player: " + data.currentPlayer)
                print("Player hands: ")
                for p in data.players:
                    print(p.toClientString())
                print("Table cards: ")
                for pos in data.tableCards:
                    print(pos + ": [ ")
                    for c in data.tableCards[pos]:
                        print(c.toClientString() + " ")
                    print("]")
                print("Discard pile: ")
                for c in data.discardPile:
                    print("\t" + c.toClientString())            
                print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
                print("Storm tokens used: " + str(data.usedStormTokens) + "/3")
                print()
                print("[" + playerName + " - " + status + "]: ", end="")
                print()
                print("Owned cards:")
                for i in memory: #print our memory
                    print(i.toClientString())
                print()
            
            index = ck.getQrow(data, memory)    # get the Qrow of the Q-table according to the environment
            
            canHint = True      # check if there aren't 8 noteTokens used
            canFold = True      # check if there are notetokens used
            if data.usedNoteTokens==8 or ck.chooseCardToHint(data,memory,hint_memory) == None:  # choose the move
                canHint = False
            if data.usedNoteTokens==0:
                canFold = False
            if not canHint and not canFold:
                move = 0
            else:
                move = qp.readQTable(Qtable, index, canHint, canFold)
                if move not in [0,1,2]:
                    print("Move error: ", move)
                    exit
            
            if move == 0:   # play
                card_index = ck.chooseCardToPlay(data,memory) #choose card to play
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, card_index).serialize())
                data = s.recv(DATASIZE)
                if not data:
                    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                    requested_show = True
                    continue
                data = GameData.GameData.deserialize(data)

                if type(data) is GameData.ServerPlayerMoveOk:  # correct move
                    print("Nice move!")
                    print("Current player: " + data.player)
                    print()
                elif type(data) is GameData.ServerPlayerThunderStrike:  # wrong move
                    print("OH NO! The Gods are unhappy with you!")
                    print("Current player: " + data.player)
                    print()
                elif type(data) is GameData.ServerGameOver:     # if the game end
                    print()
                    print(data.message)
                    print(data.score)
                    print(data.scoreMessage)
                    stdout.flush()
                    return

                played_card = memory.pop(card_index)    # update our memory
                print("Playing card in position ", card_index)
                if not played_card.color:
                    played_card.color = 'Unknown'
                if played_card.value == 0:
                    played_card.value = 'Unknown'
                print(played_card.toClientString())
                print()
                memory.append(game.Card(0,0,None))  # append the new card
                print("[" + playerName + " - " + status + "]: ", end="")
                print()
            elif move == 1:     # hint
                hint = ck.chooseCardToHint(data, memory, hint_memory)   # choose the card to hint
                if 'value' in hint:
                    value = hint['value']
                    t = 'value'
                else:
                    value = hint['color']
                    t = 'color'
                hint = {'player': hint['player'], 'value': value, 'type': t}    # save the new hint
                print("Hinting to: "+str(hint['player'])+" "+str(t)+": "+str(value))

                if hint['player'] not in hint_memory:   # update our hint_memory
                    hint_memory[data.destination] = []
                if {t: value} not in hint_memory[hint['player']]:
                    hint_memory[hint['player']].append({t: value})

                s.send(GameData.ClientHintData(playerName, hint['player'], t, value).serialize())   # execute the hint
                print()
                print("Current player: ", data.currentPlayer)
                print("[" + playerName + " - " + status + "]: ", end="")
                print()
            else:   # discard
                discard_index = ck.chooseCardToDiscard(data,memory)     # choose card to hint
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, discard_index).serialize())  # send hint

                known_discarded_card = memory.pop(discard_index)    # retrieve informations on discarded card
                memory.append(game.Card(0,0,None))      # append the new card
                print("Discarding card in position ", discard_index)
                if not known_discarded_card.color:
                    known_discarded_card.color = 'Unknown'
                if known_discarded_card.value == 0:
                    known_discarded_card.value = 'Unknown'
                print(known_discarded_card.toClientString())
                print()
                print("Current player: ", data.currentPlayer)
                print("[" + playerName + " - " + status + "]: ", end="")
                print()

        elif type(data) is GameData.ServerGameOver:
            print()
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            return
        elif requested_show:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            continue

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName) 
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
        print()
    else:
        print("Connection refused, ERROR")
        exit
    print("[" + playerName + " - " + status + "]: ", end="")
    print()
    s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerStartRequestAccepted:
            print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")
            print()
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
    else:
        print("Client not ready, ERROR")
        exit
    if type(data) is GameData.ServerStartGameData:
            print("Game start!")
            print()
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]
    else:
        print("Game not started, ERROR")
        exit
    print("[" + playerName + " - " + status + "]: ", end="")
    print()

    manageInput()