#!/usr/bin/env python3
"""Run baseline and spatial-grounded wildfire evacuation response generation.

This runner supports a transparent synthetic surrogate for v0 pipeline
validation, the OpenAI Responses API, or a local Ollama model.
"""

from __future__ import annotations

import csv
import json
import os
import random
import argparse
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pipeline_validation"
DEFAULT_PERSONAS_FILE = DATA / "personas.csv"
DEFAULT_SPATIAL_CONTEXT_FILE = DATA / "spatial_context.csv"

DECISIONS = ["Evacuate now", "Delay evacuation", "Stay", "Uncertain"]
MODES = ["Private vehicle", "Ride with family/friend", "Public transit", "Walk", "Emergency transport", "Mixed/other", "No transportation"]
DESTINATIONS = ["Public shelter", "Friend/relative home", "Hotel/motel", "Medical facility", "Outside evacuation zone", "Stay in place", "Unknown"]
RAW_FIELDNAMES = [
    "run_id",
    "condition",
    "persona_id",
    "repeat",
    "result_type",
    "model_used",
    "prompt",
    "raw_response",
    "decision",
    "transportation_mode",
    "destination_type",
    "departure_urgency",
    "key_constraints_considered",
    "reasoning",
]
FAILURE_FIELDNAMES = [
    "run_id",
    "condition",
    "persona_id",
    "repeat",
    "model_used",
    "attempts",
    "error_type",
    "error_message",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_personas(personas_file: Path, spatial_context_file: Path) -> list[dict[str, str]]:
    personas = read_csv(personas_file)
    if not spatial_context_file.exists():
        return personas
    spatial = {row["persona_id"]: row for row in read_csv(spatial_context_file)}
    merged = []
    for persona in personas:
        row = dict(persona)
        row.update(spatial.get(persona["persona_id"], {}))
        if "census_tract_or_area" not in row:
            tract = row.get("census_tract_id", "")
            label = row.get("neighborhood_label", "")
            row["census_tract_or_area"] = f"{label} ({tract})".strip()
        merged.append(row)
    return merged


def render_prompt(template: str, persona: dict[str, str]) -> str:
    return template.format(**persona)


def has_medical(persona: dict[str, str]) -> bool:
    return persona["medical_caregiving_responsibilities"] != "None"


def has_children(persona: dict[str, str]) -> bool:
    return "children" in persona["family_structure"].lower() or "child" in persona["medical_caregiving_responsibilities"].lower()


def synthetic_response(persona: dict[str, str], condition: str, repeat: int) -> str:
    """Mimic an LLM response with plausible but imperfect constraint handling."""
    rng = random.Random(f"{persona['persona_id']}-{condition}-{repeat}-20260530")
    vehicle = persona["vehicle_access"] == "Yes"
    low_income = persona["income_level"] in {"Low", "Lower-middle"}
    medical = has_medical(persona)
    children = has_children(persona)
    risk = persona["wildfire_risk_level"]
    high_risk = risk in {"High", "Very high"}
    shelter_miles = float(persona["distance_to_nearest_shelter"])
    shelter_time = int(float(persona["road_travel_time_to_shelter"]))
    hazard_miles = float(persona["distance_to_hazard_zone"])
    transit = persona["transit_access"].lower()

    if condition == "spatial_grounded":
        if high_risk or hazard_miles < 2.0 or medical:
            decision = "Evacuate now"
        elif rng.random() < 0.28:
            decision = "Delay evacuation"
        else:
            decision = "Evacuate now"
    else:
        decision = rng.choices(
            DECISIONS,
            weights=[0.58 if high_risk else 0.46, 0.24, 0.08, 0.10],
            k=1,
        )[0]

    if decision in {"Stay", "Uncertain"}:
        mode = "No transportation"
        dest = "Stay in place" if decision == "Stay" else "Unknown"
    elif condition == "spatial_grounded":
        if vehicle:
            mode = "Private vehicle"
        elif medical and (transit in {"none", "limited"} or shelter_time > 45):
            mode = rng.choice(["Emergency transport", "Ride with family/friend"])
        elif transit in {"good", "moderate"}:
            mode = rng.choice(["Public transit", "Ride with family/friend"])
        elif children or shelter_miles > 2.5:
            mode = "Ride with family/friend"
        else:
            mode = rng.choice(["Walk", "Ride with family/friend"])

        if medical and rng.random() < 0.48:
            dest = "Medical facility"
        elif low_income:
            dest = rng.choice(["Public shelter", "Friend/relative home", "Outside evacuation zone"])
        elif shelter_time > 45:
            dest = rng.choice(["Friend/relative home", "Outside evacuation zone"])
        else:
            dest = rng.choice(["Public shelter", "Friend/relative home", "Hotel/motel", "Outside evacuation zone"])
    else:
        # Baseline deliberately lacks distance/risk context and sometimes chooses infeasible options.
        if vehicle:
            mode = rng.choices(["Private vehicle", "Ride with family/friend", "Public transit"], weights=[0.78, 0.12, 0.10], k=1)[0]
        else:
            mode = rng.choices(["Public transit", "Ride with family/friend", "Walk", "Private vehicle"], weights=[0.35, 0.28, 0.22, 0.15], k=1)[0]
        if low_income:
            dest = rng.choices(["Public shelter", "Friend/relative home", "Hotel/motel", "Outside evacuation zone"], weights=[0.45, 0.24, 0.18, 0.13], k=1)[0]
        else:
            dest = rng.choice(["Public shelter", "Friend/relative home", "Hotel/motel", "Outside evacuation zone"])

    if decision == "Evacuate now":
        urgency = "Immediate" if high_risk or hazard_miles < 2.0 else "Same day"
    elif decision == "Delay evacuation":
        urgency = "Monitor and prepare"
    elif decision == "Stay":
        urgency = "No departure planned"
    else:
        urgency = "Needs more information"

    constraints = []
    if vehicle:
        constraints.append("vehicle access")
    else:
        constraints.append("no private vehicle")
    if low_income:
        constraints.append("limited lodging budget")
    if medical:
        constraints.append(persona["medical_caregiving_responsibilities"])
    if children:
        constraints.append("children/care coordination")
    if condition == "spatial_grounded":
        constraints.append(f"{shelter_miles:.1f} mi / {shelter_time} min to shelter")
        constraints.append(f"{risk.lower()} wildfire risk")

    if condition == "spatial_grounded":
        reasoning = (
            f"The household is in a {risk.lower()} risk area about {hazard_miles:.1f} miles from the hazard zone. "
            f"Given {', '.join(constraints)}, the first response should prioritize a feasible route and destination."
        )
    else:
        reasoning = (
            f"Based on the household profile, {', '.join(constraints)} shape the likely first response. "
            "The choice reflects a plausible evacuation action under worsening smoke and congestion."
        )

    return "\n".join([
        f"Persona ID: {persona['persona_id']}",
        f"Decision: {decision}",
        f"Transportation mode: {mode}",
        f"Likely destination type: {dest}",
        f"Departure urgency: {urgency}",
        f"Key constraints considered: {'; '.join(constraints)}",
        f"Reasoning: {reasoning}",
    ])


def call_openai_once(prompt: str) -> str:
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "input": prompt,
        "temperature": 0.4,
        "max_output_tokens": 450,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8")) from exc
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def call_openai(prompt: str, max_retries: int, initial_backoff: float) -> str:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):
        try:
            return call_openai_once(prompt)
        except Exception as exc:
            last_error = exc
            if attempt > max_retries:
                break
            sleep_for = initial_backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            print(f"API call failed on attempt {attempt}; retrying in {sleep_for:.1f}s: {exc}")
            time.sleep(sleep_for)
    assert last_error is not None
    raise last_error


def call_ollama_once(prompt: str) -> str:
    model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 450,
        },
    }
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        timeout = float(os.environ.get("OLLAMA_TIMEOUT", "600"))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8")) from exc
    return (data.get("response") or "").strip()


def call_with_retries(callable_fn, prompt: str, max_retries: int, initial_backoff: float, label: str) -> str:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):
        try:
            return callable_fn(prompt)
        except Exception as exc:
            last_error = exc
            if attempt > max_retries:
                break
            sleep_for = initial_backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            print(f"{label} call failed on attempt {attempt}; retrying in {sleep_for:.1f}s: {exc}")
            time.sleep(sleep_for)
    assert last_error is not None
    raise last_error


def extract(raw: str, label: str) -> str:
    prefix = f"{label}:"
    for line in raw.splitlines():
        if line.lower().startswith(prefix.lower()):
            return line.split(":", 1)[1].strip()
    return ""


def append_csv_row(path: Path, fieldnames: list[str], row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
        f.flush()


def completed_run_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    rows = read_csv(path)
    return {row["run_id"] for row in rows if row.get("run_id")}


def remove_failure_for_run(path: Path, run_id: str) -> None:
    if not path.exists():
        return
    rows = [row for row in read_csv(path) if row.get("run_id") != run_id]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FAILURE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run wildfire evacuation LLM experiment.")
    parser.add_argument("--provider", choices=["synthetic", "openai", "ollama"], default=os.environ.get("EXPERIMENT_PROVIDER", "synthetic"))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--personas-file", default=str(DEFAULT_PERSONAS_FILE))
    parser.add_argument("--spatial-context-file", default=str(DEFAULT_SPATIAL_CONTEXT_FILE))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--limit-personas", type=int, default=0, help="Limit personas for smoke tests; 0 means all personas.")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--initial-backoff", type=float, default=2.0)
    parser.add_argument("--overwrite", action="store_true", help="Delete existing raw/failure files before running.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for --provider openai. No API run was performed.")

    personas = load_personas(resolve_path(args.personas_file), resolve_path(args.spatial_context_file))
    if args.limit_personas:
        personas = personas[:args.limit_personas]
    baseline_template = (PROMPTS / "baseline_prompt_template.txt").read_text(encoding="utf-8")
    spatial_template = (PROMPTS / "spatial_grounded_prompt_template.txt").read_text(encoding="utf-8")
    use_openai = args.provider == "openai"
    use_ollama = args.provider == "ollama"
    os.environ["OPENAI_MODEL"] = args.model
    os.environ["OLLAMA_MODEL"] = args.model

    raw_path = output_dir / "llm_responses_raw.csv"
    failure_path = output_dir / "failed_runs.csv"
    if args.overwrite:
        raw_path.unlink(missing_ok=True)
        failure_path.unlink(missing_ok=True)

    completed = completed_run_ids(raw_path)
    total = len(personas) * 2 * args.repeats
    saved = skipped = failed = 0
    for persona in personas:
        for condition, template in [("baseline", baseline_template), ("spatial_grounded", spatial_template)]:
            for repeat in range(1, args.repeats + 1):
                run_id = f"{persona['persona_id']}-{condition}-r{repeat}"
                if run_id in completed:
                    skipped += 1
                    continue
                prompt = render_prompt(template, persona)
                try:
                    if use_openai:
                        raw = call_with_retries(call_openai_once, prompt, args.max_retries, args.initial_backoff, "OpenAI")
                    elif use_ollama:
                        raw = call_with_retries(call_ollama_once, prompt, args.max_retries, args.initial_backoff, "Ollama")
                    else:
                        raw = synthetic_response(persona, condition, repeat)
                    row = {
                        "run_id": run_id,
                        "condition": condition,
                        "persona_id": persona["persona_id"],
                        "repeat": repeat,
                        "result_type": "main_experiment_api" if use_openai else ("main_experiment_ollama" if use_ollama else "pipeline_validation_surrogate"),
                        "model_used": args.model if (use_openai or use_ollama) else "synthetic_rule_based_llm_surrogate",
                        "prompt": prompt,
                        "raw_response": raw,
                        "decision": extract(raw, "Decision"),
                        "transportation_mode": extract(raw, "Transportation mode"),
                        "destination_type": extract(raw, "Likely destination type"),
                        "departure_urgency": extract(raw, "Departure urgency"),
                        "key_constraints_considered": extract(raw, "Key constraints considered"),
                        "reasoning": extract(raw, "Reasoning"),
                    }
                    append_csv_row(raw_path, RAW_FIELDNAMES, row)
                    completed.add(run_id)
                    remove_failure_for_run(failure_path, run_id)
                    saved += 1
                    print(f"Saved {run_id} ({len(completed)}/{total})")
                except Exception as exc:
                    append_csv_row(failure_path, FAILURE_FIELDNAMES, {
                        "run_id": run_id,
                        "condition": condition,
                        "persona_id": persona["persona_id"],
                        "repeat": repeat,
                        "model_used": args.model if (use_openai or use_ollama) else "synthetic_rule_based_llm_surrogate",
                        "attempts": args.max_retries + 1,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    })
                    failed += 1
                    print(f"FAILED {run_id}: {exc}")

    print(f"Run complete for {output_dir}: saved={saved}, skipped={skipped}, failed={failed}, total_expected={total}")
    if failed:
        print(f"Failures were logged to {failure_path}. Re-run the same command to resume only missing runs.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
