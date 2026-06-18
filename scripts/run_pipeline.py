#!/usr/bin/env python3
"""Run the full experiment pipeline for one output namespace."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT.parent, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM evacuation pipeline.")
    parser.add_argument("--provider", choices=["synthetic", "openai", "ollama"], default="synthetic")
    parser.add_argument("--output-dir", default="project/outputs/pipeline_validation")
    parser.add_argument("--figure-dir", default="project/figures/pipeline_validation")
    parser.add_argument("--paper-dir", default="project/paper")
    parser.add_argument("--personas-file", default="project/data/personas.csv")
    parser.add_argument("--spatial-context-file", default="project/data/spatial_context.csv")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--limit-personas", type=int, default=0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--initial-backoff", type=float, default=2.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    run_cmd = [
        sys.executable,
        "project/scripts/run_llm_experiment.py",
        "--provider",
        args.provider,
        "--output-dir",
        args.output_dir,
        "--personas-file",
        args.personas_file,
        "--spatial-context-file",
        args.spatial_context_file,
        "--model",
        args.model,
        "--repeats",
        str(args.repeats),
        "--max-retries",
        str(args.max_retries),
        "--initial-backoff",
        str(args.initial_backoff),
    ]
    if args.overwrite:
        run_cmd.append("--overwrite")
    if args.limit_personas:
        run_cmd.extend(["--limit-personas", str(args.limit_personas)])
    run(run_cmd)
    run([sys.executable, "project/scripts/parse_llm_outputs.py", "--output-dir", args.output_dir])
    run([sys.executable, "project/scripts/evaluate_feasibility.py", "--output-dir", args.output_dir, "--personas-file", args.personas_file, "--spatial-context-file", args.spatial_context_file])
    run([sys.executable, "project/scripts/analyze_results.py", "--output-dir", args.output_dir, "--paper-dir", args.paper_dir, "--personas-file", args.personas_file, "--spatial-context-file", args.spatial_context_file])
    run([sys.executable, "project/scripts/make_figures.py", "--output-dir", args.output_dir, "--figure-dir", args.figure_dir])
    run([sys.executable, "project/scripts/validate_outputs.py", "--output-dir", args.output_dir, "--personas-file", args.personas_file, "--spatial-context-file", args.spatial_context_file])


if __name__ == "__main__":
    main()
