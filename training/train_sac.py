"""Explicitly gated SAC training entry point.

Running this module without --start-training only prints the plan and exits.
"""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "RL_TRAINING_PLAN.md"
DEFAULT_TRACKS = ("spa", "silverstone", "monza", "monaco", "shanghai")

STAGES = {
    1: {
        "name": "基础控车与赛道边界",
        "steps": 500_000,
        "tracks": ("monza", "silverstone"),
    },
    2: {
        "name": "全速五赛道课程",
        "steps": 1_500_000,
        "tracks": DEFAULT_TRACKS,
    },
    3: {
        "name": "独立赛车线与刹车点",
        "steps": 3_000_000,
        "tracks": DEFAULT_TRACKS,
    },
    4: {
        "name": "圈速精调与泛化",
        "steps": 2_000_000,
        "tracks": DEFAULT_TRACKS,
    },
}


def build_parser():
    parser = argparse.ArgumentParser(description="Offline SAC racing trainer")
    parser.add_argument(
        "--start-training",
        action="store_true",
        help="required safety gate; without it no environment or model is created",
    )
    parser.add_argument("--stage", type=int, choices=STAGES, default=1)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=302)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="optional Stable-Baselines3 checkpoint to continue",
    )
    return parser


def print_dry_run(args):
    stage = STAGES[args.stage]
    steps = args.steps or stage["steps"]
    print("训练未启动：缺少显式参数 --start-training。")
    print(f"计划阶段: {args.stage} - {stage['name']}")
    print(f"计划步数: {steps:,}")
    print(f"赛道: {', '.join(stage['tracks'])}")
    print(f"步骤档案: {PLAN_PATH}")


def start_training(args):
    # Heavy optional dependencies are imported only after the explicit gate.
    from stable_baselines3 import SAC
    from stable_baselines3.common.callbacks import (
        CheckpointCallback,
        EvalCallback,
    )
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

    from training.racing_env import RacingEnv

    stage = STAGES[args.stage]
    steps = args.steps or stage["steps"]
    run_dir = ROOT / "training" / "runs" / f"stage_{args.stage}"
    checkpoint_dir = ROOT / "training" / "checkpoints" / f"stage_{args.stage}"
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    env_kwargs = {
        "track_ids": stage["tracks"],
        "curriculum_stage": args.stage,
    }
    train_env = VecMonitor(
        make_vec_env(
            RacingEnv,
            n_envs=args.workers,
            seed=args.seed,
            env_kwargs=env_kwargs,
        )
    )
    eval_env = VecMonitor(
        DummyVecEnv(
            [
                lambda: RacingEnv(
                    track_ids=stage["tracks"],
                    curriculum_stage=args.stage,
                    seed=args.seed + 10_000,
                )
            ]
        )
    )

    if args.resume:
        model = SAC.load(args.resume, env=train_env, device="auto")
    else:
        model = SAC(
            "MlpPolicy",
            train_env,
            learning_rate=3e-4,
            buffer_size=1_000_000,
            learning_starts=20_000,
            batch_size=512,
            tau=0.005,
            gamma=0.995,
            train_freq=1,
            gradient_steps=1,
            ent_coef="auto",
            policy_kwargs={"net_arch": [256, 256, 128]},
            tensorboard_log=str(run_dir),
            seed=args.seed,
            verbose=1,
            device="auto",
        )

    checkpoint = CheckpointCallback(
        save_freq=max(50_000 // args.workers, 1),
        save_path=str(checkpoint_dir),
        name_prefix="sac_racing",
        save_replay_buffer=True,
    )
    evaluation = EvalCallback(
        eval_env,
        best_model_save_path=str(checkpoint_dir / "best"),
        log_path=str(run_dir / "evaluation"),
        eval_freq=max(50_000 // args.workers, 1),
        n_eval_episodes=10,
        deterministic=True,
    )
    try:
        model.learn(
            total_timesteps=steps,
            callback=[checkpoint, evaluation],
            progress_bar=True,
            reset_num_timesteps=args.resume is None,
        )
        model.save(checkpoint_dir / "final_model")
    finally:
        train_env.close()
        eval_env.close()


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.start_training:
        print_dry_run(args)
        return 0
    start_training(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
