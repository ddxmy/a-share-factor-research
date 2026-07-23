#!/usr/bin/env python3
"""Consolidate sealed per-pack parameter plans without changing their contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Parameter plan must be a JSON object or list")
    if isinstance(payload.get("factors"), dict):
        return [
            {"candidate_id": candidate_id, **specification}
            for candidate_id, specification in payload["factors"].items()
        ]
    for key in ("parameters", "parameter_plans"):
        if isinstance(payload.get(key), list):
            return payload[key]
    raise ValueError("Parameter plan has no recognized records")


def write_json_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-manifest", required=True)
    parser.add_argument("--campaign-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    campaign_path = Path(args.campaign_manifest).resolve()
    campaign_dir = Path(args.campaign_dir).resolve()
    output_path = Path(args.output).resolve()
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if campaign.get("status") != "discovery_open_validation_sealed":
        raise RuntimeError("Campaign is not open with validation sealed")

    maximum_packs = int(campaign["budgets"]["maximum_packs"])
    pack_size = int(campaign["budgets"]["pack_size"])
    combined: list[dict] = []
    sources: list[dict] = []
    seen: set[str] = set()
    for pack_number in range(1, maximum_packs + 1):
        pack_dir = campaign_dir / f"pack_{pack_number:02d}"
        manifest_path = pack_dir / "pack_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "sealed_before_discovery":
            raise RuntimeError(f"Pack {pack_number} is not sealed")
        if manifest.get("campaign_hash") != campaign["campaign_hash"]:
            raise RuntimeError(f"Pack {pack_number} campaign hash mismatch")
        plan_path = Path(manifest["parameter_plan_path"]).resolve()
        if sha256_file(plan_path) != manifest["parameter_plan_sha256"]:
            raise RuntimeError(f"Pack {pack_number} parameter plan changed after sealing")
        records = load_records(json.loads(plan_path.read_text(encoding="utf-8")))
        if len(records) != pack_size:
            raise RuntimeError(f"Pack {pack_number} does not contain {pack_size} plans")
        for record in records:
            candidate_id = str(record.get("candidate_id"))
            if candidate_id in seen:
                raise RuntimeError(f"Duplicate candidate parameter plan: {candidate_id}")
            seen.add(candidate_id)
            parameter_free = record.get("parameter_free") is True
            variants = record.get("formula_variants", [])
            if parameter_free == bool(variants):
                raise RuntimeError(f"Invalid parameter declaration for {candidate_id}")
            combined.append(record)
        sources.append(
            {
                "pack_number": pack_number,
                "pack_manifest": str(manifest_path),
                "pack_manifest_sha256": sha256_file(manifest_path),
                "parameter_plan": str(plan_path),
                "parameter_plan_sha256": sha256_file(plan_path),
            }
        )

    expected = int(campaign["budgets"]["candidate_budget"])
    if len(combined) != expected:
        raise RuntimeError(f"Expected {expected} plans, found {len(combined)}")
    combined.sort(key=lambda record: str(record["candidate_id"]))
    payload = {
        "campaign_version": campaign["campaign_version"],
        "campaign_hash": campaign["campaign_hash"],
        "status": "consolidated_from_sealed_pack_plans",
        "candidate_budget": expected,
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "source_pack_plans": sources,
        "parameter_plans": combined,
        "validation_labels_opened": False,
    }
    write_json_exclusive(output_path, payload)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "records": len(combined),
                "sha256": sha256_file(output_path),
                "validation_labels_opened": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
