from sys import argv, stdout
from threading import Thread

import GameData
import socket
from constants import *
import checks as ck
import Qprocess as qp
import game

training = ''
verbose = False
save = False
count = 0

if len(argv) < 4:
    print("You need the player name to start the game.")
    playerName = "Test" # for debug
    ip = HOST
    port = PORT
    training = 'no'
    verbose = True
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])
    if len(argv) >= 5:
        training = argv[4]  # activate a training modality
        # 'pre' for pretraining, take actions as keyboard input, but update q-table
        # 'self' for self q-learning, choose actions from q-table and update q-table
        # anything else for just playing, don't update q-table
    if len(argv) >= 6:
        verbose = argv[5]
        if verbose == 'verbose':
            verbose = True
        else:
            verbose = False
    if len(argv) >= 7:
        save = argv[6]
        if save == 'save':
            save = True
        else:
            save = False
                
statuses = ["Lobby", "Game", "GameHint"]
status = statuses[0]

move = -1           # move 0, 1, 2 -> play, hint, discard
reward = 0          # reward from the action choosed
index = -1          # index of the Q-table related to the row
next_index = -1     # next index to update the Q-table
defaultPlayer = 'steo'
window = []             # list of scores
path = './tables/Q-table.npy'  # path related to the Q-table
folder = './training'   # folder about training Q-tables
alpha = 0             # parameter alpha
gamma = 0               # parameter gamma
after50 = True          # interval of results to save

def manageInput():
    global status
    global training
    global reward
    global index
    global move
    global next_index
    global count
    global path
    global defaultPlayer
    global after50

    count += 1          # to count the number of games
    hint_memory = {}    # to store the hint about other players
    hands_memory = {}   # to store the memory about the own cards
    first_round = True  # to verify if it is the first round
    memory = [ game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None), game.Card(0,0,None) ] # known cards -> 5 card 

    if training not in ['pre','self']:
        Qtable = False
        while not Qtable:
            Qtable = qp.loadQTableFromFile(path) # list of size (256,3)

    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())      # first show to activate the s.recv(...)
    requested_show = True   # to verify if it was requested a show

    while True:
        data = s.recv(DATASIZE)
        
        if not data:    # verify if the data is correct
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            requested_show = True
            continue

        data = GameData.GameData.deserialize(data)      # deserialize data
        if type(data) is GameData.ServerHintData:       # verify if the response is an hint
            if training != 'self' or verbose:           # print the hint    
                print("Hint type: " + data.type)
                print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
                for i in data.positions:
                    print("\t" + str(i))
            if data.destination == playerName:  # if hint is for us, update our memory
                for i in data.positions:
                    if data.type =='value':
                        memory[i].value = data.value
                    else:
                        memory[i].color = data.value
                if training != 'self' or verbose:       # print the knowledge about the own cards
                    print()
                    print("Owned cards:")
                    for i in memory:                    # print our memory
                        print(i.toClientString())
            else:
                for i in data.positions:                # update the hint memory about other players
                    if data.destination not in hint_memory:
                        hint_memory[data.destination] = []
                    if {data.type: data.value} not in hint_memory[data.destination]:
                        hint_memory[data.destination].append({data.type: data.value})

            if training != 'self' or verbose:
                print()
                print("[" + playerName + " - " + status + "]: ", end="")
                print()

        elif type(data) is GameData.ServerGameOver:     # verify if the game is over
            window.append(data.score)                   # append the score about the game
            if len(window) <= 1000 and len(window)%50 == 0 and len(window) != 0:   
                mean = round(sum(window)/len(window), 2)
                rate0 = round(len([i for i in window if i == 0])/len(window)*100, 2)
                print("MEAN: ", mean, " LENGTH: ", len(window), " ZERO PERCENTAGE: ", rate0)       # print the mean about the scores and the percentage of bad games
                if (playerName == defaultPlayer and save):      # save the Q-table only if the player is the default one
                    if (after50):
                        qp.saveQTableAsFile(qp.loadQTableFromFile(path), folder+'/Q-table_'+str(mean)+'_'+str(rate0))
                    elif (len(window) == 1000):
                        qp.saveQTableAsFile(qp.loadQTableFromFile(path), folder+'/Q-table_'+str(mean)+'_'+str(rate0))
            if training != 'self':
                print()
                print(data.message)
                print(data.score)
                print(data.scoreMessage)
                if verbose:
                    print("Ready for a new game!")
                    print()

            if data.score > 0 and training == 'self':   # to print when a win is reached
                print("A WIN after: ",count)
                count = 0
                if verbose:
                    print("Ready for a new game!")
                    print()

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

        if type(data) is GameData.ServerGameStateData:      # intercept the show response
            for p in data.players:      # check if p.name is a key of hint_memory
                if p.name not in hint_memory:
                    hint_memory[p.name] = []

            if hands_memory:        # update other players' hint memory
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

                next_index = ck.getQrow(data,memory)    # update for previous play depends on its state and the new state

                if not first_round:     # verify if we are not in the first round to update the Q-table
                    if training  in ['pre', 'self']:
                        qp.updateQTable(index, next_index, move, reward, gamma, alpha, path)
                        reward = 0
                
                # choose a move
                if training == 'pre':   # if pre-training, input the move
                    print()
                    print("[" + playerName + " - " + status + "]: ", end="")
                    move = input()      # must be play, hint or discard
                    while move not in ['play', 'hint', 'discard'] or (move=='hint' and data.usedNoteTokens==8) or (move=='discard' and data.usedNoteTokens==0):
                        if move=='hint' and data.usedNoteTokens==8:
                            print("You don't have note tokens!")
                        elif move=='discard' and data.usedNoteTokens==0:
                            print("You are full of note tokens!")
                        else:
                            print("You must specify only play, hint or discard!")
                        move = input()
                    move = ['play', 'hint', 'discard'].index(move)
                else:   # if training or simply playing, choose move from Q-table
                    canHint = True
                    canFold = True
                    if data.usedNoteTokens==8 or ck.chooseCardToHint(data,memory,hint_memory) == None:      # verify if the player can hint or discard according to tokens
                        canHint = False
                    if data.usedNoteTokens==0:
                        canFold = False
                    if not canHint and not canFold:
                        move = 0
                    else:
                        if training in ['pre','self']:
                            Qtable = False
                            while not Qtable:
                                Qtable = qp.loadQTableFromFile(path) # list of size (256,3)
                        move = qp.readQTable(Qtable, next_index, canHint,canFold)
                        if move not in [0,1,2]:
                            print("Move error: ", move)
                            exit

                if move == 0:   # play
                    card_index = ck.chooseCardToPlay(data,memory)   # choose card to play
                    s.send(GameData.ClientPlayerPlayCardRequest(playerName, card_index).serialize())    # send the play request
                    data = s.recv(DATASIZE)
                    if not data:
                        s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                        requested_show = True
                        continue
                    data = GameData.GameData.deserialize(data)

                    if type(data) is GameData.ServerPlayerMoveOk:       # collect the reward
                        reward = 10 
                        if training != 'self' or verbose:
                            print("Nice move!")
                            print("Current player: " + data.player)
                            print()
                    elif type(data) is GameData.ServerPlayerThunderStrike:
                        reward = -20
                        if training != 'self' or verbose:
                            print("OH NO! The Gods are unhappy with you!")
                            print("Current player: " + data.player)
                            print()
                    elif type(data) is GameData.ServerGameOver:
                        window.append(data.score)       # collect the score after the game over
                        if len(window) <= 1000 and len(window)%50 == 0 and len(window) != 0:
                            mean = round(sum(window)/len(window), 2)
                            rate0 = round(len([i for i in window if i == 0])/len(window)*100, 2)
                            print("MEAN: ", mean, " LENGTH: ", len(window), " ZERO PERCENTAGE: ", rate0)
                            if (playerName == defaultPlayer and save):
                                if (after50):
                                    qp.saveQTableAsFile(qp.loadQTableFromFile(path), folder+'/Q-table_'+str(mean)+'_'+str(rate0))
                                elif (len(window) == 1000):
                                    qp.saveQTableAsFile(qp.loadQTableFromFile(path), folder+'/Q-table_'+str(mean)+'_'+str(rate0))
                        if training!='self':
                            print()
                            print(data.message)
                            print(data.score)
                            print(data.scoreMessage)
                            if verbose:
                                print("Ready for a new game!")
                                print()
                        if data.score > 0 and training=='self':
                            print("AFTER ",count)
                            count = 0
                            if verbose:
                                print("Ready for a new game!")
                                print()
                        stdout.flush()
                        return
                    
                    played_card = memory.pop(card_index)    # update memory
                    if training != 'self' or verbose:
                        print("Playing card in position ", card_index)
                        if not played_card.color:
                            played_card.color = 'Unknown'
                        if played_card.value == 0:
                            played_card.value = 'Unknown'
                        print(played_card.toClientString())
                        print()
                    memory.append(game.Card(0, 0, None))    # append the new card 
                    if training != 'self' or verbose:
                        print("[" + playerName + " - " + status + "]: ", end="")
                        print()

                elif move == 1:     # hint
                    hint = ck.chooseCardToHint(data,memory,hint_memory)     # choose the hint card
                    if 'value' in hint:
                        value = hint['value']
                        t = 'value'
                    else:
                        value = hint['color']
                        t = 'color'
                    hint = {'player': hint['player'], 'value': value, 'type': t}    # create the hint    

                    if training != 'self' or verbose:
                        print("Hinting to: "+str(hint['player'])+" "+str(t)+": "+str(value))

                    if hint['player'] not in hint_memory:       # update the hint memory
                        hint_memory[data.destination] = []
                    if {t: value} not in hint_memory[hint['player']]:
                        hint_memory[hint['player']].append({t: value})

                    reward = ck.computeHintReward(data,hint,memory)     # collect the reward
                    s.send(GameData.ClientHintData(playerName, hint['player'], t, value).serialize())   # execute the hint
                    if training != 'self' or verbose:
                        print()
                        print("Current player: ", data.currentPlayer)
                        print("[" + playerName + " - " + status + "]: ", end="")
                        print()

                else:   # discard
                    discard_index = ck.chooseCardToDiscard(data,memory)     # choose the card to discard
                    s.send(GameData.ClientPlayerDiscardCardRequest(playerName, discard_index).serialize())
                    old_memory = memory.copy()  # update memory
                    known_discarded_card = memory.pop(discard_index)    # retrieve informations on discarded card
                    memory.append(game.Card(0, 0, None))    # append the new card

                    reward = ck.computeDiscardReward(data, known_discarded_card, old_memory)    # obtaining the reward

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

                if first_round:     # check if it is the first round
                    first_round = False
                    continue
                index = next_index  # after the first round we can update the Q-table

        elif type(data) is GameData.ServerGameOver:     # check if the game is over
            window.append(data.score)
            if len(window) <= 1000 and len(window)%50 == 0 and len(window) != 0:
                mean = round(sum(window)/len(window), 2)
                rate0 = round(len([i for i in window if i == 0])/len(window)*100, 2)
                print("MEAN: ", mean, " LENGTH: ", len(window), " ZERO PERCENTAGE: ", rate0)
                if (playerName == defaultPlayer and save):
                    if (after50):
                        qp.saveQTableAsFile(qp.loadQTableFromFile(path), folder+'/Q-table_'+str(mean)+'_'+str(rate0))
                    elif (len(window) == 1000):
                        qp.saveQTableAsFile(qp.loadQTableFromFile(path), folder+'/Q-table_'+str(mean)+'_'+str(rate0))
            if training != 'self':
                print()
                print(data.message)
                print(data.score)
                print(data.scoreMessage)
                if verbose:
                    print("Ready for a new game!")
                    print()
            if data.score > 0 and training=='self':
                print("AFTER ",count)
                count = 0
                if verbose:
                    print("Ready for a new game!")
                    print()
            stdout.flush()
            return

        elif requested_show:    # check if the show was requested
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

    while True and not (len(window) > 1000 and save):
        manageInput()