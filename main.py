#!/usr/bin/env python3
"""Racing Line Pro — Top-Down 2D Racing Game"""

import sys, os, traceback

# PyInstaller bundle path handling
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_DIR

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

# Write crashes to a log file so we can debug
_log_path = os.path.join(APP_DIR, 'raceline_error.log')

try:
    import pygame
    import config as cfg
    from game.loop import GameLoop

    def main():
        pygame.init()
        pygame.joystick.init()
        try:
            flags = pygame.DOUBLEBUF | pygame.HWSURFACE
            if cfg.VSYNC:
                flags |= pygame.SCALED
            screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), flags)
            pygame.display.set_caption('Racing Line Pro')
            clock = pygame.time.Clock()
            game = GameLoop(screen, clock)
            game.run()
        finally:
            pygame.quit()

    if __name__ == '__main__':
        main()

except Exception:
    with open(_log_path, 'w', encoding='utf-8') as f:
        f.write("RacingLinePro CRASH\n")
        f.write(traceback.format_exc())
    # Show a message box so the user knows something happened
    if getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Racing Line Pro crashed.\n\nDetails written to:\n{_log_path}", "Racing Line Pro", 0x10)
    raise
