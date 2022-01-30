from random import random
import numpy as np

def QTableFrom0():
    Q = np.zeros((256, 3))
    np.save('Q-table-0', Q)

def randomQTable():
    Q = np.random.randint(low=-10, high=10, size=(256, 3))
    np.save('Q-table-R', Q)

def saveQTableAsFile(Q, path):
    Q = np.array(Q)
    np.save(path, Q)

def loadQTableFromFile(path='Q-table.npy'):
    return np.load(path).tolist()

def readQTable(Q, index): # index = row from checks, return the action related to the actual state of the system
    best_actions = np.where(np.array(Q[index]) == max(Q[index]))[0].tolist() # list of the indexes related to the best actions [0 play, 1 hint, 2 discard]
    ind = random.randint(0, len(best_actions)-1)
    return best_actions[ind]

def updateQTable(index, nextIndex, action, reward, gamma=0.5, alpha=0.5, path='Q-table.npy'):
    Q = loadQTableFromFile(path)
    Qnext = max(Q[nextIndex]) # value of best next action
    print((1-alpha)*Q[index][action] + alpha*(reward + gamma*Qnext))
    Q[index][action] = (1-alpha)*Q[index][action] + alpha*(reward + gamma*Qnext) # update Q
    saveQTableAsFile(Q, path)







