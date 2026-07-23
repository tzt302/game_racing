from pathlib import Path

import pygame


class EngineAudio:
    """Load- and RPM-sensitive V6 hybrid power-unit sound model."""

    BAND_RPM = (4200, 5800, 7400, 9000, 10600, 12200)

    def __init__(self):
        self.available = False
        self.texture_channels = []
        self.synth_channels = []
        self.texture_sounds = []
        self.synth_sounds = []
        self.shift_sound = None
        self.startup_sound = None
        self.scrub_sound = None
        self.turbo_sound = None
        self.overrun_sound = None
        self.scrub_channel = None
        self.turbo_channel = None
        self.overrun_channel = None
        self._last_shift = False
        self._texture_volume = [0.0] * len(self.BAND_RPM)
        self._synth_volume = [0.0] * len(self.BAND_RPM)
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=384)
            pygame.mixer.set_num_channels(max(18, pygame.mixer.get_num_channels()))
            root = Path(__file__).resolve().parents[2]
            audio_dir = root / "assets" / "audio"
            self.texture_sounds = [
                pygame.mixer.Sound(str(audio_dir / f"f1_real_{index}.wav"))
                for index in range(6)
            ]
            self.synth_sounds = [
                self._make_v6_layer(rpm) for rpm in self.BAND_RPM
            ]
            self.texture_channels = [pygame.mixer.Channel(index) for index in range(6)]
            self.synth_channels = [pygame.mixer.Channel(index + 6) for index in range(6)]
            for channels, sounds in (
                (self.texture_channels, self.texture_sounds),
                (self.synth_channels, self.synth_sounds),
            ):
                for channel, sound in zip(channels, sounds):
                    channel.play(sound, loops=-1)
                    channel.set_volume(0.0)

            self.shift_sound = self._make_shift_sound()
            self.startup_sound = pygame.mixer.Sound(
                str(audio_dir / "source" / "f1_br_06_engine_starts_4.ogg")
            )
            self.scrub_sound = self._make_scrub_sound()
            self.turbo_sound = self._make_turbo_sound()
            self.overrun_sound = self._make_overrun_sound()
            self.scrub_channel = pygame.mixer.Channel(13)
            self.turbo_channel = pygame.mixer.Channel(14)
            self.overrun_channel = pygame.mixer.Channel(15)
            for channel, sound in (
                (self.scrub_channel, self.scrub_sound),
                (self.turbo_channel, self.turbo_sound),
                (self.overrun_channel, self.overrun_sound),
            ):
                channel.play(sound, loops=-1)
                channel.set_volume(0.0)
            self.available = True
        except (pygame.error, FileNotFoundError, OSError, ValueError):
            self.available = False

    @staticmethod
    def firing_frequency(rpm):
        """A four-stroke V6 produces three combustion events per revolution."""
        return max(0.0, float(rpm)) * 3.0 / 60.0

    @classmethod
    def band_weights(cls, rpm):
        rpm = max(cls.BAND_RPM[0], min(cls.BAND_RPM[-1], float(rpm)))
        weights = [0.0] * len(cls.BAND_RPM)
        for index in range(len(cls.BAND_RPM) - 1):
            low = cls.BAND_RPM[index]
            high = cls.BAND_RPM[index + 1]
            if low <= rpm <= high:
                blend = (rpm - low) / (high - low)
                # Equal-power crossfade avoids a volume dip between recordings.
                weights[index] = (1.0 - blend) ** 0.5
                weights[index + 1] = blend ** 0.5
                break
        if not any(weights):
            weights[-1] = 1.0
        return weights

    @classmethod
    def _make_v6_layer(cls, rpm):
        import numpy as np

        rate = 44100
        duration = 0.5
        length = int(rate * duration)
        time = np.arange(length, dtype=float) / rate
        # Snap to a loop-safe frequency bin while keeping the correct V6 firing
        # relationship. Harmonics reproduce exhaust pulse and intake resonance.
        fundamental = round(cls.firing_frequency(rpm) * duration) / duration
        wave = (
            0.62 * np.sin(2 * np.pi * fundamental * time)
            + 0.28 * np.sin(2 * np.pi * fundamental * 2.0 * time + 0.35)
            + 0.16 * np.sin(2 * np.pi * fundamental * 3.0 * time + 0.80)
            + 0.08 * np.sin(2 * np.pi * fundamental * 4.0 * time + 1.20)
        )
        wave = np.tanh(wave * 1.35)
        # A slight stereo phase offset gives the exhaust spatial width without
        # causing a discontinuity at the loop boundary.
        left = wave
        right = np.roll(wave, 5)
        stereo = np.column_stack((left, right))
        return pygame.sndarray.make_sound(
            np.int16(np.clip(stereo * 11800, -32767, 32767))
        )

    @staticmethod
    def _make_shift_sound():
        import numpy as np

        rate = 44100
        length = int(rate * 0.14)
        time = np.arange(length) / rate
        envelope = np.exp(-time * 29.0)
        ignition_cut = (
            np.sin(2 * np.pi * 82 * time)
            + 0.52 * np.sin(2 * np.pi * 164 * time + 0.4)
        ) * envelope
        noise = np.random.default_rng(7).normal(0, 0.30, length) * envelope
        mono = np.int16(np.clip((ignition_cut + noise) * 13800, -32767, 32767))
        return pygame.sndarray.make_sound(np.column_stack((mono, mono)))

    @staticmethod
    def _make_scrub_sound():
        import numpy as np

        rng = np.random.default_rng(19)
        mono = rng.normal(0, 1, 11025)
        mono = np.convolve(mono, np.ones(7) / 7, mode="same")
        mono = np.int16(np.clip(mono * 9000, -32767, 32767))
        return pygame.sndarray.make_sound(np.column_stack((mono, mono)))

    @staticmethod
    def _make_turbo_sound():
        import numpy as np

        rate = 44100
        time = np.arange(rate // 2) / rate
        whistle = (
            np.sin(2 * np.pi * 1480 * time)
            + 0.34 * np.sin(2 * np.pi * 2960 * time)
        )
        stereo = np.column_stack((whistle, np.roll(whistle, 9)))
        return pygame.sndarray.make_sound(
            np.int16(np.clip(stereo * 3400, -32767, 32767))
        )

    @staticmethod
    def _make_overrun_sound():
        import numpy as np

        rate = 44100
        rng = np.random.default_rng(31)
        impulses = np.zeros(rate // 2)
        for index in rng.integers(0, len(impulses), 24):
            impulses[index : index + 45] += np.exp(-np.arange(45) / 8.0)
        rumble = np.sin(2 * np.pi * 74 * np.arange(len(impulses)) / rate)
        mono = np.int16(np.clip((impulses * 0.8 + rumble * 0.12) * 11000, -32767, 32767))
        return pygame.sndarray.make_sound(np.column_stack((mono, mono)))

    def update(self, vehicle, cockpit=False):
        if not self.available:
            return
        weights = self.band_weights(vehicle.rpm)
        throttle = max(0.0, min(1.0, vehicle.throttle))
        rpm_ratio = max(0.0, min(1.0, (vehicle.rpm - 4000.0) / 9000.0))
        power_load = 0.18 + throttle * 0.82
        if vehicle.shift_timer > 0.0:
            power_load *= 0.16
        master = 0.78 if cockpit else 1.0

        for index, weight in enumerate(weights):
            target_texture = weight * (0.22 + throttle * 0.48) * master
            target_synth = weight * power_load * (0.12 + rpm_ratio * 0.19) * master
            self._texture_volume[index] += (
                target_texture - self._texture_volume[index]
            ) * 0.24
            self._synth_volume[index] += (
                target_synth - self._synth_volume[index]
            ) * 0.24
            self.texture_channels[index].set_volume(self._texture_volume[index])
            self.synth_channels[index].set_volume(self._synth_volume[index])

        if vehicle.shift_event and not self._last_shift and self.shift_sound:
            pygame.mixer.Channel(12).play(self.shift_sound)
            pygame.mixer.Channel(12).set_volume(0.56)
        self._last_shift = vehicle.shift_event

        turbo = throttle * rpm_ratio * rpm_ratio * 0.18
        self.turbo_channel.set_volume(turbo)
        overrun = max(0.0, (rpm_ratio - 0.25) * 0.18) if throttle < 0.08 else 0.0
        self.overrun_channel.set_volume(overrun)

        scrub = min(0.55, abs(vehicle.slip_angle) * 3.8)
        if vehicle.surface == "kerb":
            scrub = max(scrub, 0.14)
        elif vehicle.surface == "runoff":
            scrub = max(scrub, 0.22)
        elif vehicle.surface == "grass":
            scrub = max(scrub, 0.34)
        self.scrub_channel.set_volume(scrub)

    def play_startup(self):
        if self.available and self.startup_sound:
            channel = pygame.mixer.Channel(16)
            channel.play(self.startup_sound)
            channel.set_volume(0.78)

    def silence(self):
        if not self.available:
            return
        for channels in (self.texture_channels, self.synth_channels):
            for channel in channels:
                channel.set_volume(0.0)
        for channel in (
            self.scrub_channel,
            self.turbo_channel,
            self.overrun_channel,
        ):
            if channel:
                channel.set_volume(0.0)

    def stop_startup(self):
        if self.available:
            pygame.mixer.Channel(16).stop()
