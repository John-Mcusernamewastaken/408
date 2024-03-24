import random
import numpy as np
import tensorflow as tf
from keras import layers
import matplotlib.pyplot as plt
from environments import MazeEnv
from agents import *
import datetime
import os
import multiprocessing as mp
import gc

#it's possible to make these three files one file, but the extra axis would make it really confusing, and this way is more convenient to run

#the parallelism is poorly implemented, but afaik there's no way to pass tf models across threads or processes, since they aren't pickleable.
#This is the best I could come up with.
#environment is defined in this function, agents are defined in main
def train(agentType, agentConfig, rngSeedInit, nEpisodes, nMetrics, metrics):
    rngSeed=rngSeedInit
    random.seed(rngSeed)
    tf.random.set_seed(rngSeed)
    np.random.seed(rngSeed)
    
    environment = MazeEnv(startPosition=[(0,0)])
    
    #in order for the child process to pass them to the agent constructor, all args must be specified, even if they're unused by this agent
    hiddenLayers, learningRate, epsilon, epsilonDecay, discountRate, entropyWeight, criticWeight, tMax, interval, replayMemoryCapacity, replayFraction = agentConfig
    agent: Agent
    agent = agentType(
        learningRate=learningRate,
        actionSpace=environment.actionSpace,
        hiddenLayers=hiddenLayers,
        validActions=environment.validActions,
        epsilon=epsilon,
        epsilonDecay=epsilonDecay,
        discountRate=discountRate,
        entropyWeight=entropyWeight,
        criticWeight=criticWeight,
        tMax=tMax,
        interval=interval,
        replayMemoryCapacity=replayMemoryCapacity,
        replayFraction=replayFraction
    )
    print("Training new " + type(environment).__name__ + " / " + type(agent).__name__)
    Ss = []
    As = []
    Rs = []
    for i in range(nEpisodes):
        #Losses = []
        observation, _ = environment.reset(rngSeed)
        observation = tf.expand_dims(tf.convert_to_tensor(observation), 0)
        Ss.append(observation) #record observation for training
        terminated = False
        truncated = False
        while not (terminated or truncated): #for each time step in episode

            #prompt agent
            action = agent.act(tf.convert_to_tensor(observation))
            As.append(action) #record action for training

            #pass action to environment, get next observation
            observation, reward, terminated, truncated, _ = environment.step(action)
            observation = tf.expand_dims(tf.convert_to_tensor(observation), 0)
            Rs.append(float(reward)) #record reward for training
            Ss.append(observation) #record observation for training
            
            agent.handleStep(terminated or truncated, Ss, As, Rs, callbacks=[
                #tf.keras.callbacks.LambdaCallback(on_episode_end=lambda _, logs: Losses.append(logs["loss"])) #for logging loss as a metric (not used atm)
            ])
        #episode finished
        sumRs = sum(Rs)
        metrics[i + (nMetrics-1)] = sumRs
        print(agentType.__name__+": Episode "+str(i)+" Done (r = "+str(sumRs)+", ε = "+str(round(agent.epsilon,2))+")")
        rngSeed+=1
        Ss.clear()
        As.clear()
        Rs.clear()
    #finished training this agent
    #write the model weights to file
    weightsPath = "checkpoints\\" + type(environment).__name__ + "_" + type(agent).__name__ + ".tf"
    agent.save_weights(weightsPath, overwrite=True)

if __name__ == "__main__":
    environment = MazeEnv
    #in order for the child processes to pass them to the agent constructor, all args must be specified, even if they're unused by this agent
    agentConfigs: list[tuple[Agent,tuple]]
    agentConfigs = [
        (PPOAgent, (
            [layers.Conv2D(1,2,(1,1)), layers.Conv2D(1,2,(1,1)), layers.Flatten(), layers.Dense(16, activation=tf.nn.sigmoid)],
            0.00001, #learning rate
            0, #epsilon
            0, #epsilon decay
            .99, #discount rate
            .1, # entropyWeight, 
            5, # criticWeight, 
            1000, # tMax,
            .2, # interval, 
            0, # replayMemoryCapacity, 
            0, # replayFraction
        )),
        (AdvantageActorCriticAgent, (
            [layers.Conv2D(1,2,(1,1)), layers.Conv2D(1,2,(1,1)), layers.Flatten(), layers.Dense(16, activation=tf.nn.sigmoid)],
            0.00001, #learning rate
            0, #epsilon
            0, #epsilon decay
            .99, #discount rate
            .1, # entropyWeight, 
            5, # criticWeight, 
            1000, # tMax,
            0, # interval, 
            0, # replayMemoryCapacity, 
            0, # replayFraction
        )),
        (ActorCriticAgent, (
            [layers.Conv2D(1,2,(1,1)), layers.Conv2D(1,2,(1,1)), layers.Flatten(), layers.Dense(16, activation=tf.nn.sigmoid)],
            0.00001, #learning rate
            0, #epsilon
            0, #epsilon decay
            .99, #discount rate
            .1, # entropyWeight, 
            5, # criticWeight, 
            0, # tMax, 
            0, # interval, 
            1000, # replayMemoryCapacity, 
            10, # replayFraction
        )),
        (DQNAgent, (
            [layers.Conv2D(1,2,(1,1)), layers.Conv2D(1,2,(1,1)), layers.Flatten(), layers.Dense(16, activation=tf.nn.sigmoid)],
            0.00001, #learning rate
            .33, #epsilon
            1, #epsilon decay
            .99, #discount rate
            0, # entropyWeight, 
            0, # criticWeight, 
            0, # tMax, 
            0, # interval, 
            1000, # replayMemoryCapacity, 
            10, # replayFraction
        )),
        (REINFORCEAgent, (
            [layers.Conv2D(1,2,(1,1)), layers.Conv2D(1,2,(1,1)), layers.Flatten(), layers.Dense(16, activation=tf.nn.sigmoid)],
            0.00001, #learning rate
            0, #epsilon
            0, #epsilon decay
            .99, #discount rate
            .1, # entropyWeight, 
            0, # criticWeight, 
            0, # tMax, 
            0, # interval, 
            0, # replayMemoryCapacity, 
            0, # replayFraction
        ))
    ]

    RNG_SEED = 0 #fixed RNG for replicability.
    N_EPISODES = 3000 #number of episodes to train for
    N_METRICS = 1 #reward
    metrics = []
    for i in range(len(agentConfigs)):
        metrics.append(mp.Array('d', N_EPISODES * N_METRICS))
    startDatetime = datetime.datetime.now()
    #Pool doesn't work here, throws due to the shared metrics variables ^
    processes = []
    for i in range(len(agentConfigs)):
        process = mp.Process(target=train, args=[
            agentConfigs[i][0],
            agentConfigs[i][1],
            RNG_SEED,
            N_EPISODES,
            N_METRICS, 
            metrics[i]
        ])
        processes.append(process)
        process.start()
    for process in processes:
        process.join()  
        #finished training all agents on this environment
    
    nonSharedMetrics = []
    for i in range(len(agentConfigs)):
        nonSharedMetrics.append([])
        for j in range(N_METRICS):
            nonSharedMetrics[i].append([])
            for k in range(N_EPISODES):
                nonSharedMetrics[i][j].append(metrics[i][k + (j-1)])
    #finished training all environments
    #write the metrics to file
    metricsDir = os.path.dirname(os.path.abspath(__file__)) + "\\metrics"
    os.makedirs(metricsDir, exist_ok=True)
    metadataAgents = [agentConfig[0].__name__ for agentConfig in agentConfigs]
    metadataEnvironments = [environment.__name__]
    np.savez(
        metricsDir + "\\metrics_" + datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S"),
        agents=metadataAgents,
        environments=metadataEnvironments,
        nEpisodes = [N_EPISODES],
        data=nonSharedMetrics
    )

    def plot(yss, j, label):
        match environment.__name__:
            case "MazeEnv":
                plt.axhline(y=4767/2, color="grey")
            case "TagEnv":
                plt.axhline(y=565/2, color="grey")
            case "TTTEnv":
                plt.axhline(y=1000/2, color="lightgrey")
        for i in range(len(agentConfigs)):
            ys = yss[i][j]
            x = range(len(ys))

            #smooth the curve
            smoothedYs = []
            window = []
            windowSize = N_EPISODES/10
            for y in ys:
                window.append(y)
                if len(window)>windowSize:
                    window.pop(0)
                smoothedYs.append(sum(window)/windowSize)
            plt.plot(x,smoothedYs, label=label + "(" + agentConfigs[i][0].__name__ + ")")
            plt.title(environment.__name__)
            plt.legend()

    #plot metrics
    plot(nonSharedMetrics, 0, "reward")

    print("Finished training after", datetime.datetime.now().__sub__(startDatetime))
    plt.show()

    input("press any key to continue") #because pyplot fails to show sometimes
    #prompt to continue training
    
    #n = input("enter number to extend training, non-numeric to end\n")
    #if(n.isnumeric()):
    #    resetEpisodes=episodes
    #    targetEpisodes+=int(n)
    #else:
    #    trainingRunning = False
    #    environments[i].close()