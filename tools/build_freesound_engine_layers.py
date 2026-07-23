"""Build loop-safe RPM textures from the credited Freesound field recording."""

import os
from pathlib import Path

import numpy as np
import pygame
from scipy import signal
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "audio" / "source" / "f1_br_06_engine_starts_4.ogg"
OUTPUT_DIR = ROOT / "assets" / "audio"
SAMPLE_RATE = 44100

# Each band samples a different moment of the real multi-car engine-start
# recording. Pitch scaling supplies a coherent RPM progression while the
# overlapping ends remove clicks at Pygame's loop boundary.
BANDS = (
    (1.20, 0.78),
    (1.62, 0.88),
    (2.08, 0.98),
    (2.60, 1.09),
    (3.18, 1.20),
    (3.76, 1.32),
)


def make_loop(recording, start_seconds, pitch_factor):
    source_length = int(SAMPLE_RATE * 1.08 * pitch_factor)
    start = int(start_seconds * SAMPLE_RATE)
    segment = recording[start : start + source_length].astype(np.float64)
    pitched_length = max(1, int(len(segment) / pitch_factor))
    pitched = signal.resample(segment, pitched_length, axis=0)

    loop_length = min(int(SAMPLE_RATE * 0.82), len(pitched) - 1)
    crossfade = min(int(SAMPLE_RATE * 0.09), len(pitched) - loop_length)
    loop = pitched[:loop_length].copy()
    fade = np.linspace(0.0, 1.0, crossfade, endpoint=False)[:, None]
    loop[:crossfade] = (
        pitched[loop_length : loop_length + crossfade] * (1.0 - fade)
        + pitched[:crossfade] * fade
    )

    # Remove recorder DC offset and use gentle saturation rather than clipping.
    loop -= np.mean(loop, axis=0, keepdims=True)
    peak = max(float(np.max(np.abs(loop))), 1.0)
    loop = np.tanh(loop / peak * 1.65)
    return np.int16(np.clip(loop * 21800, -32767, 32767))


def main():
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
    recording = pygame.sndarray.array(pygame.mixer.Sound(str(SOURCE)))
    if recording.ndim == 1:
        recording = np.column_stack((recording, recording))
    for index, (start, pitch) in enumerate(BANDS):
        output = OUTPUT_DIR / f"f1_real_{index}.wav"
        wavfile.write(output, SAMPLE_RATE, make_loop(recording, start, pitch))
        print(output.relative_to(ROOT))
    pygame.mixer.quit()


if __name__ == "__main__":
    main()
