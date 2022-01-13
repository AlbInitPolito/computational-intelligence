from sys import argv, stdout
from threading import Thread
import GameData
import socket
from constants import *
import os

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
        if training != 'True' or training != 'False':
            print("you need to specify True or False only!")
            exit(-2)
    else:
        training = False

run = True

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

hintState = ("", "")

def manageInput():
    global run
    global status

    # serve a tornare nell'if di show se non vengono ricevute le info di show dopo averle richieste
    requested_show = False

    # show inutile: ci serve solo per attivare la prima volta s.recv
    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
    requested_show = True

    while run:

        #aspettiamo che qualcuno faccia una mossa
        data = s.recv(DATASIZE)

        #intercettiamo un hint ricevuto per non perderlo
        # DA FARE implementare una memoria locale per gli hint ricevuti
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerHintData and data.destination == playerName:
            if not training:
                print("Hint type: " + data.type)
                print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
                for i in data.positions:
                    print("\t" + str(i))

        # facciamo sempre uno show per 1) sapere se tocca a noi 2) se tocca a noi, aggiornare gli stati
        s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        requested_show = True
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)

        # se abbiamo ricevuto dati di show
        # aggiorniamo gli stati DA FARE
        if type(data) is GameData.ServerGameStateData:
            requested_show = False
            #se non tocca a noi, torniamo su e continuiamo ad aspettare
            if data.currentPlayer != playerName:
                continue
            if not training:
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
    else:
        print("ERR1")
        exit
    print("[" + playerName + " - " + status + "]: ", end="")
    s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerStartRequestAccepted:
            print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
    else:
        print("ERR2")
        exit
    if type(data) is GameData.ServerStartGameData:
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]
    else:
        print("ERR3")
        exit
    print("[" + playerName + " - " + status + "]: ", end="")

    manageInput()