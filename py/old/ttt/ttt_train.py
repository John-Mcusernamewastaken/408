import random
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from jgw_cs408.environments.ttt_env import TTTEnv, TTTSearchAgent
from jgw_cs408.agents import *
import time

if __name__ == "__main__":
    RNG_SEED_INIT=42
    TRAINING_TIME_SECONDS = 300
    EPSILON_EVALUATION_WINDOW_SIZE = 3 #epsilon is lowered (difficulty is increased) if the agent scores well in at least this many games in a row
    EPSILON_TARGET = .5 #stop training if epsilon lowers below this value
    EPSILON_DROP_RATE = 100900

    env = TTTEnv(opponent=TTTSearchAgent(epsilon=1)) #epsilon is decreased based on highest agent performance
    agents = [
        #DQNAgent(learningRate=.001, discountRate=.95, replayMemoryCapacity=1000, epsilon=0.25, epsilonDecay=.9, actionSpace=env.actionSpace)
        REINFORCE_MENTAgent(learningRate=0.01, discountRate=.9, actionSpace=env.actionSpace, validActions=env.validActions)
        #AdvantageActorCriticAgent(learningRate=.001, actionSpace=env.actionSpace, discountRate=.75, epsilon=.99, epsilonDecay=.9999, validActions=env.validActions),
        #ActorCriticAgent(learningRate=.001, actionSpace=env.actionSpace, discountRate=.75, replayMemoryCapacity=50000, replayFraction=500, epsilon=.99, epsilonDecay=.9999, validActions=env.validActions),

    ]
    metrics = {"reward":[], "loss":[]} #list of rewards each epoch, for each agent
    for i in range(len(agents)):
        metrics["reward"].append(list())
        metrics["loss"].append(list())
    random.seed(RNG_SEED_INIT)
    tf.random.set_seed(RNG_SEED_INIT)
    np.random.seed(RNG_SEED_INIT)
    
    for i in range(len(agents)):
        rngSeed=RNG_SEED_INIT
        observation, _ = env.reset()
        observation = tf.expand_dims(tf.convert_to_tensor(observation),0)
        start = time.time()
        epochs = 0
        window = []
        while time.time()-start<=TRAINING_TIME_SECONDS and env.model.opponent.epsilon>EPSILON_TARGET:
            Ss = []
            As = []
            Rs = []
            Losses = []
            epochRunning = True
            while epochRunning: #for each time step in epoch
                Ss.append(observation) #record observation for training

                #prompt agent
                action = agents[i].act(tf.convert_to_tensor(observation))
                As.append(action) #record observation for training

                #pass action to env, get next observation
                nextObservation, reward, terminated, truncated, _ = env.step(action)
                Rs.append(float(reward)) #record observation for training
                
                nextObservation = tf.convert_to_tensor(nextObservation)
                nextObservation = tf.expand_dims(nextObservation,0)

                agents[i].handleStep(terminated or truncated, Ss, As, Rs, callbacks=[
                    tf.keras.callbacks.LambdaCallback(on_epoch_end=lambda epoch, logs: Losses.append(logs["loss"]))
                ])
                
                if terminated or truncated:
                    nextObservation, _ = env.reset(seed=rngSeed)
                    nextObservation = tf.convert_to_tensor(nextObservation)
                    nextObservation = tf.expand_dims(nextObservation,0)
                    
                    metrics["reward"][i].append(sum(Rs)) #calc overall reward for graph
                    metrics["loss"][i].extend(Losses) #calc overall reward for graph
                    Ss = []
                    As = []
                    Rs = []
                    epochRunning = False

                    #consider lowering epsilon
                    if len(window)==EPSILON_EVALUATION_WINDOW_SIZE:
                        worstOfWindow = np.min(window)
                        if worstOfWindow>0:
                            env.model.opponent.epsilon -= worstOfWindow/EPSILON_DROP_RATE
                            window = []
                        else:
                            window.pop(0)
                    window.append(metrics["reward"][i][-1])

                    print("Epoch ", epochs, " Done (r = ", metrics["reward"][i][-1],", εA ≈ ", round(agents[i].epsilon, 2),", εO ≈ ", round(env.model.opponent.epsilon, 2),")", sep="")
                observation = nextObservation
            epochs+=1
            rngSeed+=1
        #finished training this agent
    #finished training all agents
            
        #save the agents
        for agent in agents:
            #path = "checkpoints\\" + type(agent).__name__ + "_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".tf"
            path = "checkpoints\\TTT" + type(agent).__name__ + ".tf"
            agent.save_weights(path, overwrite=True)
        
        def plot(target, agents, yss, metricName):
            for i in range(len(agents)):
                ys = yss[i]
                x = range(len(ys))
                
                #smooth the curve
                smoothedYs = []
                window = []
                windowSize = 5#max(len(ys)/200, 1)
                for y in ys:
                    window.append(y)
                    if len(window)>windowSize:
                        window.pop(0)
                    smoothedYs.append(sum(window)/windowSize)
                target.plot(x,smoothedYs, label=metricName + "(" + type(agents[i]).__name__ + ")")
                #m, c = np.polyfit(x,ys,1)
                #plt.plot(m*x + c) #line of best fit
            target.legend()

        #plot return over time for each agent
        if not plt.get_fignums() == []:
            plt.clf() #clear previous graph
        fig, axs = plt.subplots(len(metrics))
        i = 0
        for k in metrics:
            plot(axs[i], agents, metrics[k], k)
            i+=1
        plt.show()
        
        #prompt to continue training
        
        #n = input("enter number to extend training, non-numeric to end\n")
        #if(n.isnumeric()):
        #    resetEpochs=epochs
        #    targetEpochs+=int(n)
        #else:
        #    trainingRunning = False
        #    envs[i].close()
    exit()   