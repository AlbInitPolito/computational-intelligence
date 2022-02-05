# Computational Intelligence 2021-2022

Exam of computational intelligence 2021 - 2022. It requires teaching the client to play the game of Hanabi (rules can be found [here](https://www.spillehulen.dk/media/102616/hanabi-card-game-rules.pdf)).

# Server

The server accepts passing objects provided in GameData.py back and forth to the clients.
Each object has a ```serialize()``` and a ```deserialize(data: str)``` method that must be used to pass the data between server and client.

Watch out! I'd suggest to keep everything in the same folder, since serialization looks dependent on the import path (thanks Paolo Rabino for letting me know).

Server closes when no client is connected.

To start the server:

```bash
python server.py <minNumPlayers>
```

Arguments:

+ minNumPlayers, __optional__: game does not start until a minimum number of player has been reached. Default = 2


Commands for server:

+ exit: exit from the server

# Client and Training

To start the client (client.py and old_client.py):

```bash
python client.py <IP> <PORT> <playerName>
```

To start the training client (training_client.py):

```bash
python client.py <IP> <PORT> <PlayerName> <training> <verbose> <save>
```

Arguments of **client.py** and **old_client.py**:

+ **IP**: IP address of the server (for localhost: 127.0.0.1)
+ **PORT**: server TCP port (default: 1024)
+ **playerName**: the name of the player, it must be

Arguments of **training_client.py** whiche must be isert **in the same order riported below**:
+ **IP**: IP address of the server (for localhost: 127.0.0.1)
+ **PORT**: server TCP port (default: 1024)
+ **playerName**: the name of the player, it must be:
  1. *"squillero"* if you want to save the Q-tables
  2. *any other name* if you don't want to save the Q-tables
+ **trainig** - it must be insert one of:
  1. *"self"* if you want a self-training approach
  2. *"pre"* if you want a manual-training approach
  3. *any other word* if you don't want to train
+ **verbose** - it must be insert one of:
  1. *"verbose"* if you want a clear output of the games
  2. *any other word* if you don't want output about the evolution of the games
+ **save** - it must be one of:
  1. *"save"* if you want to save the Q-tables after 50 iteration in the training folder
  2. *any other word* if you don't want to save the Q-tables after 50 iteration in the training folder

## Commands for clients:
The clients are automatic. These commands could be used on **old_client.py**, in particular:

+ exit: exit from the game
+ ready: set your status to ready (lobby only)
+ show: show cards
+ hint \<type> \<destinatary>:
  + type: 'color' or 'value'
  + destinatary: name of the person you want to ask the hint to
+ discard \<num>: discard the card *num* (\[0-4]) from your hand

# Students
- Alberto Castrignanò, s281689
- Stefano Rainò, s282436

