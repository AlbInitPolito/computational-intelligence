import random
import numpy as np

def QTableFrom0():
    Q = np.zeros((256, 3))
    np.save('Q-table-0', Q)

def randomQTable():
    Q = np.random.randint(low=-10, high=10, size=(256, 3))
    np.save('Q-table-R', Q)

def saveQTableAsFile(Q, path):
    try:
        Q = np.array(Q)
        np.save(path, Q)
        return True
    except:
        return False

def loadQTableFromFile(path='Q-table.npy'):
    while True:
        try:
            return np.load(path,allow_pickle=True).tolist()
        except:
            return False


def readQTable(Q, index, canHint=True, canFold=True): # index = row from checks, return the action related to the actual state of the system
    if not canHint:
        tempQ = Q[index].copy()
        tempQ.pop(1)
        best_actions = np.where(np.array(tempQ) == max(tempQ))[0].tolist()
    elif not canFold:
        tempQ = Q[index].copy()
        tempQ.pop(2)
        best_actions = np.where(np.array(tempQ) == max(tempQ))[0].tolist()
    else:
        best_actions = np.where(np.array(Q[index]) == max(Q[index]))[0].tolist() # list of the indexes related to the best actions [0 play, 1 hint, 2 discard]
    ind = random.randint(0, len(best_actions)-1)
    if not canHint:
        if best_actions[ind] == 1:
            return 2
    return best_actions[ind]

def updateQTable(index, nextIndex, action, reward, gamma=0.2, alpha=0.9, path='Q-table.npy'):
    Q = False
    while not Q:
        Q = loadQTableFromFile(path)
    Qnext = max(Q[nextIndex]) # value of best next action
    actual = Q[index].copy()
    Q[index][action] = round((1-alpha)*Q[index][action] + alpha*(reward + gamma*Qnext),2) # update Q
    #if len([i for i,j in zip(actual,Q[index]) if i==j])==3:
    #    print("DIDN'T UPDATE!!!!!!!!!!!!!!!!!!")
    outcome = False
    while not outcome:
        outcome = saveQTableAsFile(Q, path)

def printQTable(path='Q-table.npy'):
    Q = loadQTableFromFile(path)
    print(Q)


if __name__ == "__main__":
    #QTableFrom0()
    printQTable()
