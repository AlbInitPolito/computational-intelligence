from sys import argv, stdout
from threading import Thread

from sympy import continued_fraction_periodic
import GameData
import socket
from constants import *
import os
import checks as ck
import Qprocess as qp
import game

training = ''

if len(argv) < 4:
    print("You need the player name to start the game.")
    #exit(-1)
    playerName = "Test" # For debug
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])
    if len(argv) == 5:
        #attiva la modalità di training se Vero, gli output se Falso
        training = argv[4]
        # 'pre' for pretraining, take actions as keyboard input, but update q-table
        # 'self' for self q-learning, choose actions from q-table and update q-table
        # anything else for just playing, don't update q-table

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

hintState = ("", "") # ????????? todo

def manageInput():
    global status
    global training

    run = True
    first_round = True

    memory = [ game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None) ] # known cards -> 5 card 


    # serve a tornare nell'if di show se non vengono ricevute le info di show dopo averle richieste
    requested_show = False

    # show inutile: ci serve solo per attivare la prima volta s.recv
    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
    requested_show = True

    Qtable = qp.loadQTableFromFile() # list of size (256,3)

    while run:

        # aspettiamo che qualcuno faccia una mossa
        data = s.recv(DATASIZE)

        # intercettiamo gli hint per non perderli
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerHintData:
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
                for i in memory: #print our memory
                    print(i.toClientString())
        
            print()
            print("[" + playerName + " - " + status + "]: ", end="")

        # facciamo sempre uno show per 1) sapere se tocca a noi 2) se tocca a noi, aggiornare gli stati
        s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        requested_show = True
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)

        # se abbiamo ricevuto dati di show
        # aggiorniamo gli stati DA FARE
        if type(data) is GameData.ServerGameStateData:
            requested_show = False
            # se non tocca a noi, torniamo su e continuiamo ad aspettare
            if data.currentPlayer != playerName:
                continue
            # se in training, evitiamo tanti output
            else:
                if training != 'self' and training != 'pre':
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

                index = -1

                next_index = ck.getQrow(data,memory) #update for previous play depends on its state and the new state
               
                #choose a move
                if training == 'pre': # if pre-training, input the move
                    move = input() # must be play, hint or discard
                    while move not in ['play', 'hint', 'discard']:
                        print("you must specify only play, hint or discard!")
                        move = input()
                    continue
                else: #if training or simply playin, choose move from q-table
                    move = qp.readQTable(Qtable,next_index)
                    if move==0:
                        move = 'play'
                    elif move==1:
                        move = 'hint'
                    elif move==2:
                        move = 'discard'
                    else:
                        print("move error: ", move)
                        exit

                # execute the move
                if move == 'play':
                    index = ck.chooseCardToPlay(data,memory) #choose card to play
                    s.send(GameData.ClientPlayerPlayCardRequest(playerName, index).serialize())
                    data = s.recv(DATASIZE)

                    #collect the reward
                    if type(data) is GameData.ServerPlayerMoveOk:
                        reward = 10
                        if training not in ['pre', 'self']:
                            print("Nice move!")
                            print("Current player: " + data.player)
                    if type(data) is GameData.ServerPlayerThunderStrike:
                        reward = -20
                        if training not in ['pre', 'self']:
                            print("OH NO! The Gods are unhappy with you!")
                            print("Current player: " + data.player)

                    #update memory
                    played_card = memory.pop(index)
                    if training not in ['pre', 'self']:
                        print("Playing card in position ", index)
                        if not played_card.color:
                            played_card.color = 'Unknown'
                        if played_card.value == 0:
                            played_card.value = 'Unknown'
                        print(played_card.toClientString())
                        print()
                    memory.append(game.Card(0,0,None))

                elif move == 'hint':
                    hint = ck.chooseCardToHint(data,memory)
                    if 'value' in hint:
                        value = hint['value']
                        t = 'value'
                    else:
                        value = hint['color']
                        t = 'color'
                    s.send(GameData.ClientHintData(playerName, hint['player'], t, value).serialize())

                    

                    continue
                else: #discard
                    index = ck.chooseCardToDiscard(data,memory)
                    s.send(GameData.ClientPlayerDiscardCardRequest(playerName, index).serialize())

                    #update memory
                    old_memory = memory.copy()
                    known_discarded_card = memory.pop(index) #retrieve informations on discarded card

                    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                    requested_show = True
                    # richiediamo uno show
                    # se non riceviamo uno show, ed è un hint, salviamo
                    # in ogni caso, rimaniamo nel while
                    while requested_show:
                        data = s.recv(DATASIZE)
                        # intercettiamo gli hint per non perderli
                        data = GameData.GameData.deserialize(data)
                        if type(data) is GameData.ServerHintData:
                            if data.destination == playerName: #if hint is for us, update our memory
                                for i in data.positions:
                                    if data.type =='value':
                                        memory[i].value = data.value
                                    else:
                                        memory[i].color = data.value

                        if type(data) is not GameData.ServerGameStateData:
                            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                            continue
                        else: # check last discard pile card
                            requested_show = False
                            discarded_card = data.discardPile[-1]

                    #obtain the reward
                    #pass data, discarded_card, known_discarded_card, old_memory
                    reward = ck.computeDiscardReward(data,discarded_card,known_discarded_card,old_memory)

                    if training not in ['pre', 'self']:
                        print("Discarding card in position ", index)
                        if not known_discarded_card.color:
                            known_discarded_card.color = 'Unknown'
                        if known_discarded_card.value == 0:
                            known_discarded_card.value = 'Unknown'
                        print(known_discarded_card.toClientString())
                        print()
                    memory.append(game.Card(0,0,None))

                if not first_round:
                    continue
                        


                # dopo il primo round, possiamo iniziare ad aggiornare la Q-table
                index = next_index
                first_round = False

        # se lo show è stato richiesto ma è stato perso, lo richiediamo
        elif requested_show:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            continue

        ##executed after any behavior


        continue

        command = input()
        # Choose data to send
        if command == "show" and status == statuses[1]:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        elif command.split(" ")[0] == "discard" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue
        elif command.split(" ")[0] == "play" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue
        elif command.split(" ")[0] == "hint" and status == statuses[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print("Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(playerName, destination, t, value).serialize())
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue
        elif command == "":
            print("[" + playerName + " - " + status + "]: ", end="")
        else:
            print("Unknown command: " + command)
            continue
        stdout.flush()

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
        print("ERR1")
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
        print("ERR2")
        exit
    if type(data) is GameData.ServerStartGameData:
            print("Game start!")
            print()
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]
    else:
        print("ERR3")
        exit
    print("[" + playerName + " - " + status + "]: ", end="")
    print()

    while True:
        manageInput()