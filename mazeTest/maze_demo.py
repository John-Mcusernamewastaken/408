from maze_env import MazeEnv
import tensorflow as tf
from time import sleep
from maze_agents import *

if __name__ == "__main__":
    model = ActorCriticAgent(0,0,0,0)
    model.load_weights("checkpoints\MazeActorCriticAgent.tf") #TODO

    env = MazeEnv(nCoins=10, startPosition="random", render_mode="human")
    observation, _ = env.reset()
    observation = tf.expand_dims(tf.expand_dims(tf.convert_to_tensor(observation),2),0)
    totalReward=0
    while True:
        #prompt agent
        action = model.act(observation)
        print("action:", action)
        #pass action to env, get next observation
        observation, reward, terminated, truncated, _ = env.step(action)
        observation = tf.expand_dims(tf.expand_dims(tf.convert_to_tensor(observation),2),0)
        totalReward+=reward
        #epoch ends, reset env, observation, & reward
        if terminated or truncated:
            print("Reward:", totalReward)
            totalReward=0
            observation, _ = env.reset()
            observation = tf.expand_dims(tf.expand_dims(tf.convert_to_tensor(observation),2),0)
        sleep(.1)