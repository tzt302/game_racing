import pygame
import config as cfg

class InputHandler:
    def __init__(self):
        self.steer = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.reset_pressed = False
        self.pause_pressed = False
        self.joystick = None
        self._init_joystick()

    def _init_joystick(self):
        try:
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                print(f'Gamepad detected: {self.joystick.get_name()}')
        except Exception as e:
            print(f'No gamepad: {e}')

    def update(self, events):
        self.steer = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.reset_pressed = False
        self.pause_pressed = False

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    self.reset_pressed = True
                if e.key == pygame.K_ESCAPE:
                    self.pause_pressed = True
            if e.type == pygame.JOYBUTTONDOWN:
                if e.button == 0:    # A
                    self.reset_pressed = True
                if e.button == 7:    # Start
                    self.pause_pressed = True
            if e.type == pygame.JOYAXISMOTION:
                pass  # handled below per-frame

        # Keyboard
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.steer = -1.0
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.steer = 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.throttle = 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.brake = 1.0

        # Gamepad override
        if self.joystick:
            try:
                jx = self.joystick.get_axis(0)
                if abs(jx) > cfg.GAMEPAD_DEADZONE:
                    self.steer = jx
                rt = self.joystick.get_axis(5)  # RT (right trigger)
                if rt > cfg.GAMEPAD_DEADZONE:
                    self.throttle = (rt + 1.0) / 2.0
                lt = self.joystick.get_axis(4)  # LT (left trigger)
                if lt > cfg.GAMEPAD_DEADZONE:
                    self.brake = (lt + 1.0) / 2.0
                # DPAD up = throttle, down = brake
                hat = self.joystick.get_hat(0)
                if hat[1] > 0:
                    self.throttle = max(self.throttle, hat[1])
                if hat[1] < 0:
                    self.brake = max(self.brake, abs(hat[1]))
            except:
                pass
