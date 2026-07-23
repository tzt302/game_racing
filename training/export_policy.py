"""Export a trained SB3 SAC actor to the game's dependency-free NPZ format."""

import argparse
import json
from pathlib import Path

import numpy as np


def export_actor(model_path, output_path):
    from stable_baselines3 import SAC
    import torch

    model = SAC.load(model_path, device="cpu")
    linear_layers = [
        layer
        for layer in list(model.actor.latent_pi) + [model.actor.mu]
        if isinstance(layer, torch.nn.Linear)
    ]
    arrays = {}
    for index, layer in enumerate(linear_layers):
        arrays[f"weight_{index}"] = layer.weight.detach().cpu().numpy()
        arrays[f"bias_{index}"] = layer.bias.detach().cpu().numpy()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **arrays)
    metadata = {
        "format": "game_racing_numpy_mlp_v1",
        "algorithm": "SAC",
        "observation_size": int(model.observation_space.shape[0]),
        "action_size": int(model.action_space.shape[0]),
        "layer_count": len(linear_layers),
    }
    output_path.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--confirm-export",
        action="store_true",
        help="required because export loads a trained model",
    )
    args = parser.parse_args(argv)
    if not args.confirm_export:
        print("未导出：请检查模型后显式加入 --confirm-export。")
        return 0
    export_actor(args.model, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
