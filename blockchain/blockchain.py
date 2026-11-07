"""Audit ledger lokal GOVSAFE berbasis linked hash dan SHA-256."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from database import db_manager

GENESIS_PREVIOUS = "0" * 64


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def calculate_hash(block: dict[str, Any]) -> str:
    content = {
        "index": int(block["index"]),
        "timestamp": str(block["timestamp"]),
        "event_type": str(block["event_type"]),
        "payload_json": str(block["payload_json"]),
        "previous_hash": str(block["previous_hash"]),
    }
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def create_genesis_block(db_path=None) -> dict[str, Any]:
    existing = db_manager.get_blocks(db_path)
    if existing:
        return existing[0]
    block = {
        "index": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event_type": "GENESIS",
        "payload_json": canonical_json({"message": "GOVSAFE local asset audit ledger"}),
        "previous_hash": GENESIS_PREVIOUS,
    }
    block["current_hash"] = calculate_hash(block)
    db_manager.insert_block(block, db_path)
    return block


def add_block(event_type: str, payload: dict[str, Any], db_path=None) -> dict[str, Any]:
    if not event_type or event_type == "GENESIS":
        raise ValueError("Jenis event tidak valid.")
    create_genesis_block(db_path)
    blocks = db_manager.get_blocks(db_path)
    if not validate_chain(blocks):
        raise RuntimeError("Ledger tidak valid; blok baru tidak dapat ditambahkan.")
    latest = blocks[-1]
    block = {
        "index": int(latest["index"]) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event_type": event_type,
        "payload_json": canonical_json(payload),
        "previous_hash": latest["current_hash"],
    }
    block["current_hash"] = calculate_hash(block)
    db_manager.insert_block(block, db_path)
    return block


def validate_chain(blocks: list[dict[str, Any]] | None = None, db_path=None) -> bool:
    chain = db_manager.get_blocks(db_path) if blocks is None else blocks
    if not chain or int(chain[0]["index"]) != 0:
        return False
    previous = GENESIS_PREVIOUS
    for expected_index, block in enumerate(chain):
        try:
            if int(block["index"]) != expected_index or block["previous_hash"] != previous:
                return False
            payload = json.loads(block["payload_json"])
            if not isinstance(payload, dict) or canonical_json(payload) != block["payload_json"]:
                return False
            if block["event_type"] == "GENESIS" and expected_index != 0:
                return False
            if expected_index == 0 and block["event_type"] != "GENESIS":
                return False
            if calculate_hash(block) != block["current_hash"]:
                return False
            previous = block["current_hash"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False
    return True


def get_latest_block(db_path=None):
    blocks = db_manager.get_blocks(db_path)
    return blocks[-1] if blocks else None


def get_all_blocks(db_path=None):
    return db_manager.get_blocks(db_path)
