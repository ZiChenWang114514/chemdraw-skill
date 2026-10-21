from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile

import requests


MODELS = (
    {
        "key": "standard",
        "name": "DECIMER",
        "url": "https://zenodo.org/records/8300489/files/models.zip?download=1",
        "md5": "de78c966b0d63b290cd3f70bb81a91e7",
        "marker": "DECIMER_model/saved_model.pb",
    },
    {
        "key": "handdrawn",
        "name": "DECIMER_HandDrawn",
        "url": "https://zenodo.org/records/10781330/files/DECIMER_HandDrawn_model.zip?download=1",
        "md5": "1fece9813549417440f7c45d0c51603a",
        "marker": "DECIMER_HandDrawn_model/saved_model.pb",
    },
)


def download(url: str, destination: Path, proxy: str | None) -> None:
    proxies = {"http": proxy, "https": proxy} if proxy else None
    with requests.get(url, stream=True, timeout=(30, 300), proxies=proxies) as response:
        response.raise_for_status()
        with destination.open("xb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5(path: Path) -> str:
    return file_hash(path, "md5")


def sha256(path: Path) -> str:
    return file_hash(path, "sha256")


def safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"Archive symbolic links are not allowed: {member.filename}")
        bundle.extractall(destination)


def select_models(keys: list[str] | None) -> list[dict[str, str]]:
    requested = list(keys or ["all"])
    known = {model["key"] for model in MODELS}
    unknown = sorted(set(requested) - known - {"all"})
    if unknown:
        raise ValueError(f"unknown DECIMER model selection: {', '.join(unknown)}")
    if "all" in requested:
        return list(MODELS)
    return [model for model in MODELS if model["key"] in set(requested)]


def _existing_receipt(marker: Path, model: dict[str, str]) -> dict | None:
    receipt = marker.parent / ".model.json"
    if not marker.is_file() or not receipt.is_file():
        return None
    try:
        metadata = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if metadata.get("url") != model["url"] or metadata.get("md5") != model["md5"]:
        return None
    sha = metadata.get("sha256")
    return metadata if isinstance(sha, str) and len(sha) == 64 else None


def _publish_model(staged_model: Path, final_model: Path) -> None:
    backup = final_model.with_name(
        f".{final_model.name}.backup-{uuid.uuid4().hex}"
    )
    had_existing = final_model.exists()
    if had_existing:
        final_model.rename(backup)
    try:
        staged_model.rename(final_model)
    except Exception:
        if had_existing and backup.exists() and not final_model.exists():
            backup.rename(final_model)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def install_model(
    model: dict[str, str],
    target: Path,
    *,
    proxy: str | None,
    downloader=download,
) -> dict[str, str]:
    target = Path(target).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    marker = target / model["marker"]
    existing = _existing_receipt(marker, model)
    if existing:
        return {
            "name": model["name"],
            "status": "already_installed",
            "sha256": existing["sha256"],
            "marker": str(marker),
        }

    with tempfile.TemporaryDirectory(
        prefix=".decimer-install-", dir=target.parent
    ) as temporary_directory:
        stage = Path(temporary_directory)
        archive = stage / "model.zip"
        extracted = stage / "extracted"
        extracted.mkdir()
        downloader(model["url"], archive, proxy)
        actual_md5 = md5(archive)
        if actual_md5.lower() != model["md5"].lower():
            raise RuntimeError(
                f"MD5 mismatch for {model['name']}: expected {model['md5']}, got {actual_md5}"
            )
        actual_sha256 = sha256(archive)
        safe_extract(archive, extracted)
        staged_marker = extracted / model["marker"]
        if not staged_marker.is_file() or staged_marker.stat().st_size == 0:
            raise RuntimeError(f"Expected model marker was not installed: {staged_marker}")
        model_root_name = Path(model["marker"]).parts[0]
        staged_model = extracted / model_root_name
        receipt = {
            "schema_version": 1,
            "name": model["name"],
            "url": model["url"],
            "md5": actual_md5,
            "sha256": actual_sha256,
        }
        (staged_model / ".model.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        (staged_model / ".model_url").write_text(
            model["url"] + "\n", encoding="utf-8"
        )
        _publish_model(staged_model, target / model_root_name)

    return {
        "name": model["name"],
        "status": "installed",
        "sha256": actual_sha256,
        "marker": str(marker),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install official DECIMER model weights")
    parser.add_argument("--proxy", help="Optional HTTP proxy, for example http://127.0.0.1:7897")
    parser.add_argument("--target", default=str(Path.home() / ".data" / "DECIMER-V2"))
    parser.add_argument(
        "--model",
        action="append",
        choices=("standard", "handdrawn", "all"),
        help="Model to install; repeat for multiple models (default: all)",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    results = []
    for model in select_models(args.model):
        print(f"{model['name']}: checking {model['url']}")
        result = install_model(model, target, proxy=args.proxy)
        results.append(result)
        print(f"{model['name']}: {result['status']} sha256={result['sha256']}")
    print(json.dumps({"ok": True, "target": str(target), "models": results}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"DECIMER model installation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
