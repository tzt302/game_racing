from pathlib import Path

import pygame


class EngineAudio:
    """RPM-layered engine, shift transient and tyre/surface feedback."""

    def __init__(self):
        self.available = False
        self.engine_channels = []
        self.engine_sounds = []
        self.shift_sound = None
        self.scrub_sound = None
        self.scrub_channel = None
        self._last_shift = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(max(10, pygame.mixer.get_num_channels()))
            root = Path(__file__).resolve().parents[2]
            audio_dir = root / "assets" / "audio"
            self.engine_sounds = [
                pygame.mixer.Sound(str(audio_dir / f"engine_{index}.wav"))
                for index in range(6)
            ]
            self.engine_channels = [pygame.mixer.Channel(index) for index in range(6)]
            for channel, sound in zip(self.engine_channels, self.engine_sounds):
                channel.play(sound, loops=-1)
                channel.set_volume(0.0)
            self.shift_sound = self._make_shift_sound()
            self.scrub_sound = self._make_scrub_sound()
            self.scrub_channel = pygame.mixer.Channel(7)
            self.scrub_channel.play(self.scrub_sound, loops=-1)
            self.scrub_channel.set_volume(0.0)
            self.available = True
        except (pygame.error, FileNotFoundError, OSError):
            self.available = False

    @staticmethod
    def _make_shift_sound():
        import numpy as np

        rate = 44100
        length = int(rate * 0.11)
        time = np.arange(length) / rate
        envelope = np.exp(-time * 34.0)
        tone = np.sin(2 * np.pi * 92 * time) * envelope
        noise = np.random.default_rng(7).normal(0, 0.25, length) * envelope
        mono = np.int16(np.clip((tone + noise) * 15000, -32767, 32767))
        stereo = np.column_stack((mono, mono))
        return pygame.sndarray.make_sound(stereo)

    @staticmethod
    def _make_scrub_sound():
        import numpy as np

        rng = np.random.default_rng(19)
        mono = rng.normal(0, 1, 11025)
        mono = np.convolve(mono, np.ones(7) / 7, mode="same")
        mono = np.int16(np.clip(mono * 9000, -32767, 32767))
        return pygame.sndarray.make_sound(np.column_stack((mono, mono)))

    def update(self, vehicle, cockpit=False):
        if not self.available:
            return
        band = max(0.0, min(5.0, (vehicle.rpm - 4300) / (12600 - 4300) * 5.0))
        low = int(band)
        high = min(5, low + 1)
        blend = band - low
        load = 0.22 + vehicle.throttle * 0.58
        if vehicle.shift_timer > 0:
            load *= 0.22
        if cockpit:
            load *= 0.78
        for index, channel in enumerate(self.engine_channels):
            volume = 0.0
            if index == low:
                volume = (1.0 - blend) * load
            if index == high:
                volume = max(volume, blend * load)
            channel.set_volume(volume)

        if vehicle.shift_event and not self._last_shift and self.shift_sound:
            pygame.mixer.Channel(6).play(self.shift_sound)
            pygame.mixer.Channel(6).set_volume(0.48)
        self._last_shift = vehicle.shift_event

        scrub = min(0.55, abs(vehicle.slip_angle) * 3.8)
        if vehicle.surface == "kerb":
            scrub = max(scrub, 0.14)
        elif vehicle.surface == "runoff":
            scrub = max(scrub, 0.22)
        elif vehicle.surface == "grass":
            scrub = max(scrub, 0.34)
        self.scrub_channel.set_volume(scrub)

    def silence(self):
        if not self.available:
            return
        for channel in self.engine_channels:
            channel.set_volume(0.0)
        if self.scrub_channel:
            self.scrub_channel.set_volume(0.0)
