"""Poll the four Mode A Data API paths and write a Usage Board snapshot."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from agentbench.board import join_board, resolve_write_path, write_board
from agentbench.openrouter_data import DataAPIClient, fetch_payloads, load_fixture_payloads


def poll(*, out: Path | None = None, force_fixture: bool = False) -> dict:
    dest = resolve_write_path(out)
    if force_fixture or not (os.environ.get("OPENROUTER_API_KEY") or "").strip():
        payloads = load_fixture_payloads()
    else:
        payloads = fetch_payloads(DataAPIClient())
    board = join_board(payloads)
    write_board(board, dest)
    return board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Poll OpenRouter Data API (GET-only) into a board snapshot.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write path (overrides OPENROUTER_BOARD_PATH). Throwaway smokes only.",
    )
    parser.add_argument("--fixture", action="store_true", help="Write the committed fixture snapshot (no network).")
    args = parser.parse_args(argv)
    dest = resolve_write_path(args.out)
    board = poll(out=dest, force_fixture=args.fixture)
    meta = board["meta"]
    print(f"wrote {dest} live={meta['live']} rows={meta['row_count']} as_of={meta['as_of']}")
    print(meta["citation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
