#!/usr/bin/env python3
"""Racing Line Pro — Top-Down 2D Racing Game"""

import sys, os
# Add project root and src directory to path
_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, 'src'))

import pygame
import config as cfg
from game.loop import GameLoop

def main():
    pygame.init()
    pygame.joystick.init()
    flags = pygame.DOUBLEBUF | pygame.HWSURFACE
    if cfg.VSYNC:
        flags |= pygame.SCALED
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), flags)
    pygame.display.set_caption('Racing Line Pro')
    clock = pygame.time.Clock()
    game = GameLoop(screen, clock)
    game.run()
    pygame.quit()

if __name__ == '__main__':
    main()