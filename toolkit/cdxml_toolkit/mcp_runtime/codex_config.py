"""Preserve-format updater for the Codex cdxml-toolkit MCP registration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import tomlkit


SERVER_NAME = "cdxml-toolkit"
SERVER_ARGS = ["-m", "cdxml_toolkit.mcp_runtime", "--profile", "codex"]
REQUIRED_ENV = {
    "TF_CPP_MIN_LOG_LEVEL": "3",
    "TF_ENABLE_ONEDNN_OPTS": "0",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_config(
    config_path: str | os.PathLike[str],
    python_path: str | os.PathLike[str],
    *,
    expected_sha256: str | None = None,
) -> dict:
    """Update one MCP table while preserving unrelated TOML content and settings."""
    config = Path(config_path).expanduser().resolve()
    python = Path(python_path).expanduser().resolve()
    if not python.is_file():
        raise FileNotFoundError(f"Python runtime does not exist: {python}")
    original = config.read_bytes() if config.exists() else b""
    actual_hash = hashlib.sha256(original).hexdigest()
    if expected_sha256 and actual_hash.lower() != expected_sha256.lower():
        raise RuntimeError("config.toml changed after its backup was created")
    document = tomlkit.parse(original.decode("utf-8")) if original else tomlkit.document()
    servers = document.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        document["mcp_servers"] = servers
    server = servers.get(SERVER_NAME)
    if server is None:
        server = tomlkit.table()
        servers[SERVER_NAME] = server
    server["command"] = str(python)
    server["args"] = list(SERVER_ARGS)
    environment = server.get("env")
    if environment is None:
        environment = tomlkit.table()
        server["env"] = environment
    for name, value in REQUIRED_ENV.items():
        environment[name] = value

    rendered = tomlkit.dumps(document).encode("utf-8")
    if rendered == original:
        return {
            "ok": True,
            "changed": False,
            "config": str(config),
            "environment_keys": sorted(environment),
        }
    if config.exists() and _sha256(config) != actual_hash:
        raise RuntimeError("config.toml changed while the update was prepared")
    config.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{config.name}.", suffix=".tmp", dir=config.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        if config.exists() and _sha256(config) != actual_hash:
            raise RuntimeError("config.toml changed before publication")
        os.replace(temporary, config)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "ok": True,
        "changed": True,
        "config": str(config),
        "environment_keys": sorted(environment),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args(argv)
    result = update_config(
        args.config,
        args.python,
        expected_sha256=args.expected_sha256,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
