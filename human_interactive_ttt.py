from time import sleep
from environments import TTTEnv, Team, TTTSearchAgent
from agents import *
import pygame
import tensorflow as tf

env = TTTEnv(render_mode="human", opponent=None)
opponent = TTTSearchAgent(None,epsilon=.75)
env.OPPONENT = opponent

env.reset()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYDOWN:
            match(event.key):
                case pygame.K_ESCAPE:
                    exit()
        elif event.type == pygame.MOUSEBUTTONDOWN: #this must be in the main thread due to pygame shenanigans
            if pygame.mouse.get_pressed()[0]: #if it was a left click
                x,y = pygame.mouse.get_pos()
                #screen coords to grid coords
                x=int(x/env.view.xSize)
                y=int(y/env.view.ySize)
                #grid coord to action
                action = x + y*env.SIZE
                if env.board[y][x] == Team.EMPTY:
                    env.step(action) #take action
                else:
                    print("Invalid move.")
    sleep(.1)
    if env.terminated or env.truncated:
        sleep(1)
        _ = env.reset()
