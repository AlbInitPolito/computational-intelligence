from sys import argv, stdout
from threading import Thread

#from sympy import continued_fraction_periodic
import GameData
import socket
from constants import *
import os
import checks as ck
import Qprocess as qp
import game
import time
import select

training = 'no'
verbose = True
count = 0

if len(argv) < 4:
    print("You need the player name to start the game.")
    #exit(-1)
    playerName = "Test" # For debug
    ip = HOST
    port = PORT
    training = "no"
    verbose = True
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])
    training = ''
    if len(argv) >= 5:
        #attiva una modalità di training o meno
        training = argv[4]
        # 'pre' for pretraining, take actions as keyboard input, but update q-table
        # 'self' for self q-learning, choose actions from q-table and update q-table
        # anything else for just playing, don't update q-table
    if len(argv) == 6:
        verbose = argv[5]
        if verbose == 'no':
            verbose = False
        else:
            verbose = True
        

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

hint_memory = {} #memory of hints to other players
hands_memory = {} #memory of other players

move = -1
reward = 0
index = -1
next_index = -1

window = []

def manageInput():
    global status
    global training
    global reward
    global index
    global move
    global hint_memory
    global next_index
    global count
    global window

    if training not in ['self','pre']:
        Qtable = False
        while not Qtable:
            Qtable = qp.loadQTableFromFile() # list of size (256,3)

    count += 1

    hint_memory = {}

    #time.sleep(3.0)

    run = True
    first_round = True

    Qtable = False
    while not Qtable:
        Qtable = qp.loadQTableFromFile() # list of size (256,3)

    memory = [ game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None) ] # known cards -> 5 card 

    # serve a tornare nell'if di show se non vengono ricevute le info di show dopo averle richieste
    requested_show = False

    #ready = select.select([s], [], [], 3.0)

    # show inutile: ci serve solo per attivare la prima volta s.recv
    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
    requested_show = True

    while run:

        # aspettiamo che qualcuno faccia una mossa
        #if ready[0]:
        #    data = s.recv(DATASIZE)
        #else:
        #    break
        '''
        try:
            if training != 'pre':
                s.settimeout(4)
            data = s.recv(DATASIZE)
        except:
            if training != 'pre':
                print("timeout")
                return
        '''

        data = s.recv(DATASIZE)
        
        if not data:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            requested_show = True
            continue

        # intercettiamo gli hint per non perderli
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerHintData:
            if training != 'self' or verbose:
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
                if training != 'self' or verbose:
                    print()
                    print("Owned cards:")
                    for i in memory: #print our memory
                        print(i.toClientString())
            else:
                for i in data.positions:
                    if data.destination not in hint_memory:
                        hint_memory[data.destination] = []
                    if {data.type: data.value} not in hint_memory[data.destination]:
                        hint_memory[data.destination].append({data.type: data.value})

            if training != 'self' or verbose:
                print()
                print("[" + playerName + " - " + status + "]: ", end="")
                print()
        
        elif type(data) is GameData.ServerGameOver:
            
            '''
            if training == 'self':
                if len(window)==200:
                    window.pop(0)
                window.append(data.score)
                mov = round(sum(window)/len(window),2)
                print("MEDIA MOBILE ("+str(len(window))+"): "+str(mov))
            '''
            
            if data.score > 0 or training!='self':
                print()
                print(data.message)
                print(data.score)
                print(data.scoreMessage)
            if data.score > 0 and training=='self':
                print("AFTER ",count)
                count = 0

            if training != 'self' or verbose:
                print("Ready for a new game!")
                print()
            stdout.flush()
            return

        # facciamo sempre uno show per 1) sapere se tocca a noi 2) se tocca a noi, aggiornare gli stati
        s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        requested_show = True
        data = s.recv(DATASIZE)
        if not data:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            requested_show = True
            continue
        data = GameData.GameData.deserialize(data)

        # se abbiamo ricevuto dati di show
        # aggiorniamo gli stati DA FARE
        if type(data) is GameData.ServerGameStateData:

            #print("TOKENS: ",8-data.usedNoteTokens)

            for p in data.players:
                if p.name not in hint_memory:
                    hint_memory[p.name] = []

            if hands_memory:
                #update other players' hint memory
                for p in data.players:
                    if p.name != playerName:
                        for c in p.hand:
                            if c.id not in [i.id for i in hands_memory[p.name] if i.id==c.id]:
                                #print(c.toClientString())
                                # hint_memory[p.name] -> lista di hint
                                #print("HINT MEMORY BEFORE: ", hint_memory)
                                color_hints = [i for i in hint_memory[p.name] if list(i.keys())[0]=='color']
                                value_hints = [i for i in hint_memory[p.name] if list(i.keys())[0]=='value']
                                #print("COLOR HINTS: ", color_hints)
                                #print("VALUE HINTS: ", value_hints)
                                hint_memory[p.name] = list(filter(lambda x : x['color']!=c.color, color_hints))
                                hint_memory[p.name] = hint_memory[p.name] + list(filter(lambda x : x['value']!=c.value, value_hints))
                                #print("HINT MEMORY AFTER: ", hint_memory)

            # update other players' hand knowledge
            for p in data.players:
                if p.name != playerName:
                    hands_memory[p.name] = p.hand.copy()

            requested_show = False
            # se non tocca a noi, torniamo su e continuiamo ad aspettare
            if data.currentPlayer != playerName:
                continue
            # se in training, evitiamo tanti output
            else:
                if training != 'self' or verbose:
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
                #else:
                #    print("TOKENS: ", 8-data.usedNoteTokens)

                next_index = ck.getQrow(data,memory) #update for previous play depends on its state and the new state

                if not first_round:
                    if training  in ['pre', 'self']:
                        qp.updateQTable(index,next_index,move,reward)
                        reward = 0
                
                #choose a move
                if training == 'pre': # if pre-training, input the move
                    print()
                    print("[" + playerName + " - " + status + "]: ", end="")
                    move = input() # must be play, hint or discard
                    while move not in ['play', 'hint', 'discard'] or (move=='hint' and data.usedNoteTokens==8) \
                                                    or (move=='discard' and data.usedNoteTokens==0):
                        if move=='hint' and data.usedNoteTokens==8:
                            print("You don't have note tokens!")
                        elif move=='discard' and data.usedNoteTokens==0:
                            print("You are full of note tokens!")
                        else:
                            print("you must specify only play, hint or discard!")
                        move = input()
                    move = ['play', 'hint', 'discard'].index(move)
                else: #if training or simply playin, choose move from q-table
                    canHint = True
                    canFold = True
                    if data.usedNoteTokens==8 or ck.chooseCardToHint(data,memory,hint_memory) == None:
                        canHint = False
                    if data.usedNoteTokens==0:
                        canFold = False
                    if not canHint and not canFold:
                        move = 0
                    else:
                        if training in ['self','pre']:
                            Qtable = False
                            while not Qtable:
                                Qtable = qp.loadQTableFromFile() # list of size (256,3)
                        
                        move = qp.readQTable(Qtable,next_index,canHint,canFold)
                        if move not in [0,1,2]:
                            print("move error: ", move)
                            exit

                # execute the move play
                if move == 0:
                    card_index = ck.chooseCardToPlay(data,memory) #choose card to play
                    s.send(GameData.ClientPlayerPlayCardRequest(playerName, card_index).serialize())
                    data = s.recv(DATASIZE)
                    if not data:
                        s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                        requested_show = True
                        continue
                    data = GameData.GameData.deserialize(data)

                    #collect the reward
                    if type(data) is GameData.ServerPlayerMoveOk:
                        reward = 10
                        if training != 'self' or verbose:
                            print("Nice move!")
                            print("Current player: " + data.player)
                    elif type(data) is GameData.ServerPlayerThunderStrike:
                        reward = -20
                        if training != 'self' or verbose:
                            print("OH NO! The Gods are unhappy with you!")
                            print("Current player: " + data.player)
                    elif type(data) is GameData.ServerGameOver:
                        if training == 'self':

                            '''
                            if len(window)==200:
                                window.pop(0)
                            window.append(data.score)
                            mov = round(sum(window)/len(window),2)
                            print("MEDIA MOBILE ("+str(len(window))+"): "+str(mov))
                            '''
                        if data.score > 0 or training!='self':
                            print()
                            print(data.message)
                            print(data.score)
                            print(data.scoreMessage)
                        if data.score > 0 and training=='self':
                            print("AFTER ",count)
                            count = 0
                        
                        if training != 'self' or verbose:
                            print("Ready for a new game!")
                            print()
                        stdout.flush()
                        return

                    #update memory
                    played_card = memory.pop(card_index)
                    if training != 'self' or verbose:
                        print("Playing card in position ", card_index)
                        if not played_card.color:
                            played_card.color = 'Unknown'
                        if played_card.value == 0:
                            played_card.value = 'Unknown'
                        print(played_card.toClientString())
                        print()
                    memory.append(game.Card(0,0,None))

                    if training != 'self' or verbose:
                        print("[" + playerName + " - " + status + "]: ", end="")
                        print()

                #execute the move hint
                elif move == 1:
                    hint = ck.chooseCardToHint(data,memory,hint_memory)
                    if 'value' in hint:
                        value = hint['value']
                        t = 'value'
                    else:
                        value = hint['color']
                        t = 'color'
                    hint = {'player': hint['player'], 'value': value, 'type': t} 

                    if training != 'self' or verbose:
                        print("Hinting to: "+str(hint['player'])+" "+str(t)+": "+str(value))

                    if hint['player'] not in hint_memory:
                        hint_memory[data.destination] = []
                    if {t: value} not in hint_memory[hint['player']]:
                        hint_memory[hint['player']].append({t: value})

                    #collect the reward
                    reward = ck.computeHintReward(data,hint,memory)

                    #execute the hint
                    s.send(GameData.ClientHintData(playerName, hint['player'], t, value).serialize())

                    if training != 'self' or verbose:
                        print()
                        print("Current player: ", data.currentPlayer)
                        print("[" + playerName + " - " + status + "]: ", end="")
                        print()

                #execute the move discard
                else:
                    discard_index = ck.chooseCardToDiscard(data,memory)
                    s.send(GameData.ClientPlayerDiscardCardRequest(playerName, discard_index).serialize())

                    #update memory
                    old_memory = memory.copy()
                    known_discarded_card = memory.pop(discard_index) #retrieve informations on discarded card
                    memory.append(game.Card(0,0,None))

                    #obtain the reward
                    #pass data, discarded_card, old_memory
                    reward = ck.computeDiscardReward(data,known_discarded_card,old_memory)

                    if training != 'self' or verbose:
                        print("Discarding card in position ", discard_index)
                        if not known_discarded_card.color:
                            known_discarded_card.color = 'Unknown'
                        if known_discarded_card.value == 0:
                            known_discarded_card.value = 'Unknown'
                        print(known_discarded_card.toClientString())
                        print()

                    if training != 'self' or verbose:
                        print("Current player: ", data.currentPlayer)
                        print("[" + playerName + " - " + status + "]: ", end="")
                        print()

                if first_round:
                    first_round = False
                    continue
                        
                # index, next_index, reward, move
                #print()
                #print("MOVE: ", move)
                #print("REWARD: ", reward)
                #print()

                # dopo il primo round, possiamo iniziare ad aggiornare la Q-table
                index = next_index

        elif type(data) is GameData.ServerGameOver:
            if training == 'self':
                '''
                if len(window)==200:
                    window.pop(0)
                window.append(data.score)
                mov = round(sum(window)/len(window),2)
                print("MEDIA MOBILE ("+str(len(window))+"): "+str(mov))
                '''
            if data.score > 0 or training!='self':
                print()
                print(data.message)
                print(data.score)
                print(data.scoreMessage)
            if data.score > 0 and training=='self':
                print("AFTER ",count)
                count = 0
                
            if training != 'self' or verbose:
                print("Ready for a new game!")
                print()
            stdout.flush()
            return

        # se lo show è stato richiesto ma è stato perso, lo richiediamo
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