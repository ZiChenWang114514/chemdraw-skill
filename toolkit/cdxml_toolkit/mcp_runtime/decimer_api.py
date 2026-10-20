"""Client for the Steinbeck Lab DECIMER OCSR HTTP API."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
from io import BytesIO
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid
import warnings


DEFAULT_ENDPOINT = "https://api.naturalproducts.net/latest/ocsr/process-upload"
OPENAPI_URL = "https://api.naturalproducts.net/latest/openapi.json"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_MAX_IMAGE_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000
DEFAULT_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


class DecimerAPIError(RuntimeError):
    """Raised when the remote DECIMER service cannot return usable SMILES."""

    def __init__(self, message: str, *, preflight: dict[str, Any] | None = None):
        super().__init__(message)
        self.preflight = preflight

    def as_result(self) -> dict[str, Any]:
        result: dict[str, Any] = {"ok": False, "error": str(self)}
        if self.preflight is not None:
            result["preflight"] = self.preflight
        return result


class DecimerUploadRefused(DecimerAPIError):
    """Raised when upload consent is absent or does not match the prepared upload."""


def normalize_api_payload(payload: Any) -> dict[str, Any]:
    """Normalize both the documented string and live list response shapes."""
    if not isinstance(payload, dict):
        raise DecimerAPIError("DECIMER API returned a non-object JSON response")

    raw_smiles = payload.get("smiles")
    if isinstance(raw_smiles, str):
        smiles = [raw_smiles] if raw_smiles.strip() else []
    elif isinstance(raw_smiles, list):
        smiles = [value for value in raw_smiles if isinstance(value, str) and value.strip()]
    else:
        detail = payload.get("detail") or payload.get("error") or "missing smiles field"
        raise DecimerAPIError(
            f"DECIMER API response is unusable: {_sanitize_error_detail(detail)}"
        )

    if not smiles:
        raise DecimerAPIError("DECIMER API returned no SMILES predictions")
    return {"reference": payload.get("reference"), "smiles": smiles}


def build_multipart_body(
    *,
    filename: str,
    mime_type: str,
    image_bytes: bytes,
    hand_drawn: bool,
    boundary: str | None = None,
) -> tuple[str, bytes]:
    """Encode the multipart fields declared by the live OpenAPI document."""
    boundary = boundary or f"----codex-decimer-{uuid.uuid4().hex}"
    safe_name = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
    chunks = [
        f"--{boundary}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="hand_drawn"\r\n\r\n',
        ("true" if hand_drawn else "false").encode("ascii"),
        b"\r\n",
        f"--{boundary}\r\n".encode("ascii"),
        f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'.encode(
            "utf-8"
        ),
        f"Content-Type: {mime_type}\r\n\r\n".encode("ascii"),
        image_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode("ascii"),
    ]
    return f"multipart/form-data; boundary={boundary}", b"".join(chunks)


def _validate_smiles(smiles: str, index: int) -> dict[str, Any]:
    item: dict[str, Any] = {"index": index, "smiles": smiles}
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors

        molecule = Chem.MolFromSmiles(smiles)
        item["valid"] = molecule is not None
        if molecule is not None:
            item["formula"] = rdMolDescriptors.CalcMolFormula(molecule)
            item["molecular_weight"] = round(Descriptors.MolWt(molecule), 4)
    except Exception as exc:  # Validation is useful metadata, not a transport requirement.
        item["valid"] = None
        item["validation_error"] = str(exc)
    return item


def _positive_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise DecimerAPIError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise DecimerAPIError(f"{name} must be a positive integer")
    return value


def _canonical_origin(url: str, *, approval: bool = False) -> str:
    label = "approved_origin" if approval else "DECIMER_API_URL"
    if not isinstance(url, str) or not url.strip():
        raise DecimerAPIError(f"{label} must be an absolute HTTPS URL")
    if "\\" in url or any(ord(character) < 32 for character in url):
        raise DecimerAPIError(f"{label} contains invalid URL characters")
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise DecimerAPIError(f"{label} is not a valid URL") from exc
    if scheme != "https" or not hostname:
        raise DecimerAPIError(f"{label} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise DecimerAPIError(f"{label} must not include URL userinfo")
    if parsed.query:
        raise DecimerAPIError(f"{label} must not include query parameters or URL secrets")
    if parsed.fragment:
        raise DecimerAPIError(f"{label} must not include a URL fragment")
    if approval and (parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise DecimerAPIError("approved_origin must contain only a canonical origin")

    try:
        host = _canonical_host(hostname)
    except ValueError as exc:
        raise DecimerAPIError(f"{label} contains an invalid hostname") from exc
    port_suffix = "" if port in {None, 443} else f":{port}"
    return f"{scheme}://{host}{port_suffix}"


def _canonical_host(hostname: str) -> str:
    host = hostname.rstrip(".")
    if not host:
        raise ValueError("empty hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            ascii_host = host.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("invalid IDNA hostname") from exc
        if len(ascii_host) > 253:
            raise ValueError("hostname is too long")
        labels = ascii_host.split(".")
        if any(
            not label
            or len(label) > 63
            or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
            for label in labels
        ):
            raise ValueError("invalid DNS hostname")
        return ascii_host
    if address.version == 6:
        return f"[{address.compressed}]"
    return address.compressed


def _redacted_origin(url: str) -> str:
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError):
        return "<redacted-url>"
    if scheme not in {"http", "https"} or not hostname:
        return "<redacted-url>"
    try:
        host = _canonical_host(hostname)
    except ValueError:
        return "<redacted-url>"
    default_port = 443 if scheme == "https" else 80
    port_suffix = "" if port in {None, default_port} else f":{port}"
    return f"{scheme}://{host}{port_suffix}"


def _sanitize_error_detail(detail: Any) -> str:
    text = str(detail)
    sanitized = _URL_PATTERN.sub(lambda match: _redacted_origin(match.group(0)), text)
    return sanitized[:1000]


class _SameOriginHTTPSRedirectHandler(HTTPRedirectHandler):
    def __init__(self, expected_origin: str):
        super().__init__()
        self.expected_origin = expected_origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target_url = urljoin(req.full_url, newurl)
        try:
            target_scheme = urlsplit(target_url).scheme.lower()
        except (TypeError, ValueError) as exc:
            raise DecimerAPIError("DECIMER redirect target is invalid") from exc
        if target_scheme != "https":
            raise DecimerAPIError("DECIMER HTTPS downgrade redirect refused")
        try:
            target_origin = _canonical_origin(target_url)
        except DecimerAPIError as exc:
            raise DecimerAPIError(f"DECIMER redirect target refused: {exc}") from exc
        if target_origin != self.expected_origin:
            raise DecimerAPIError("DECIMER cross-origin redirect refused")
        return super().redirect_request(req, fp, code, msg, headers, target_url)


def urlopen(request: Request, *, timeout: int):
    """Open a request with redirect checks applied before a redirected upload."""
    expected_origin = _canonical_origin(request.full_url)
    opener = build_opener(_SameOriginHTTPSRedirectHandler(expected_origin))
    return opener.open(request, timeout=timeout)


def _validate_final_url(response: Any, initial_url: str, expected_origin: str) -> str:
    getter = getattr(response, "geturl", None)
    final_url = getter() if callable(getter) else initial_url
    if not isinstance(final_url, str):
        final_url = initial_url
    try:
        final_origin = _canonical_origin(final_url)
    except DecimerAPIError as exc:
        raise DecimerAPIError(f"DECIMER API final URL rejected: {exc}") from exc
    if final_origin != expected_origin:
        raise DecimerAPIError("DECIMER API final URL changed to a cross-origin destination")
    return final_origin


def _read_image_bytes(source: Path, max_bytes: int) -> bytes:
    try:
        file_stat = source.stat()
    except (OSError, ValueError) as exc:
        raise DecimerAPIError(f"Could not stat image file: {source}: {exc}") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise DecimerAPIError(f"Image path is not a regular file: {source}")
    if file_stat.st_size <= 0:
        raise DecimerAPIError(f"Image file is empty: {source}")
    if file_stat.st_size > max_bytes:
        raise DecimerAPIError(
            "Image exceeds DECIMER_API_MAX_IMAGE_BYTES "
            f"({file_stat.st_size} > {max_bytes})"
        )

    try:
        with source.open("rb") as stream:
            opened_stat = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened_stat.st_mode):
                raise DecimerAPIError(f"Image path is not a regular file: {source}")
            if opened_stat.st_size > max_bytes:
                raise DecimerAPIError(
                    "Image exceeds DECIMER_API_MAX_IMAGE_BYTES "
                    f"({opened_stat.st_size} > {max_bytes})"
                )
            image_bytes = stream.read(max_bytes + 1)
    except DecimerAPIError:
        raise
    except OSError as exc:
        raise DecimerAPIError(f"Could not read image file: {source}: {exc}") from exc
    if not image_bytes:
        raise DecimerAPIError(f"Image file is empty: {source}")
    if len(image_bytes) > max_bytes:
        raise DecimerAPIError(
            f"Image exceeds DECIMER_API_MAX_IMAGE_BYTES ({len(image_bytes)} > {max_bytes})"
        )
    return image_bytes


def _prepare_destination(output_path: str, source: Path) -> Path:
    try:
        destination = Path(output_path).expanduser().resolve()
    except (OSError, ValueError) as exc:
        raise DecimerAPIError(f"Could not resolve DECIMER output path: {exc}") from exc
    if destination == source:
        raise DecimerAPIError(f"Refusing to overwrite the source image: {destination}")
    try:
        destination.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise DecimerAPIError(f"Could not inspect DECIMER output path: {exc}") from exc
    else:
        raise DecimerAPIError(f"Refusing to overwrite an existing file: {destination}")
    if destination.parent.exists() and not destination.parent.is_dir():
        raise DecimerAPIError(
            f"DECIMER output parent is not a directory: {destination.parent}"
        )
    descriptor = -1
    probe: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, probe_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".preflight",
            dir=destination.parent,
        )
        probe = Path(probe_name)
    except OSError as exc:
        raise DecimerAPIError(
            f"Could not prepare DECIMER output directory: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if probe is not None:
            try:
                probe.unlink()
            except OSError:
                pass
    return destination


def _atomic_write_json(destination: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2).encode("utf-8")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DecimerAPIError(f"Could not prepare DECIMER output directory: {exc}") from exc

    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise DecimerAPIError(
                f"Refusing to overwrite an existing file: {destination}"
            ) from exc
        except OSError as exc:
            raise DecimerAPIError(f"Could not install DECIMER result atomically: {exc}") from exc
    except DecimerAPIError:
        raise
    except OSError as exc:
        raise DecimerAPIError(f"Could not write DECIMER result: {exc}") from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _decode_image(
    image_bytes: bytes,
    source: Path,
    *,
    max_pixels: int,
) -> tuple[str, tuple[int, int], str]:
    try:
        from PIL import Image
    except (ImportError, OSError) as exc:
        raise DecimerAPIError("Pillow is required to decode DECIMER upload images") from exc

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as image:
                image_format = image.format
                dimensions = image.size
                if dimensions[0] <= 0 or dimensions[1] <= 0:
                    raise DecimerAPIError(
                        f"Image decode returned invalid dimensions: {dimensions}"
                    )
                pixel_count = dimensions[0] * dimensions[1]
                if pixel_count > max_pixels:
                    raise DecimerAPIError(
                        "Image exceeds DECIMER_API_MAX_IMAGE_PIXELS "
                        f"({pixel_count} > {max_pixels})"
                    )
                image.load()
                mime_type = Image.MIME.get(image_format or "")
    except DecimerAPIError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise DecimerAPIError(f"Image decompression bomb rejected for {source}") from exc
    except Exception as exc:
        raise DecimerAPIError(f"Image decode failed for {source}: {exc}") from exc
    if not image_format or not mime_type:
        raise DecimerAPIError(
            f"Decoded image format has no supported MIME type: {image_format or 'unknown'}"
        )
    return image_format, dimensions, mime_type


def _refuse_upload(message: str, preflight: dict[str, Any]) -> None:
    raise DecimerUploadRefused(message, preflight=preflight)


def recognize_image(
    image_path: str,
    *,
    hand_drawn: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    output_path: str | None = None,
    confirm_upload: bool = False,
    approved_sha256: str | None = None,
    approved_origin: str | None = None,
) -> dict[str, Any]:
    """Upload one image to DECIMER and return normalized, validated predictions."""
    if timeout_seconds <= 0:
        raise DecimerAPIError("timeout_seconds must be positive")
    source = Path(image_path).expanduser().resolve()
    max_bytes = _positive_env_int("DECIMER_API_MAX_IMAGE_BYTES", DEFAULT_MAX_IMAGE_BYTES)
    max_pixels = _positive_env_int(
        "DECIMER_API_MAX_IMAGE_PIXELS", DEFAULT_MAX_IMAGE_PIXELS
    )
    max_response = _positive_env_int(
        "DECIMER_API_MAX_RESPONSE_BYTES", DEFAULT_MAX_RESPONSE_BYTES
    )
    image_bytes = _read_image_bytes(source, max_bytes)
    image_format, dimensions, mime_type = _decode_image(
        image_bytes, source, max_pixels=max_pixels
    )
    destination = _prepare_destination(output_path, source) if output_path else None
    endpoint = os.environ.get("DECIMER_API_URL", DEFAULT_ENDPOINT).strip()
    api_origin = _canonical_origin(endpoint)
    public_api_url = DEFAULT_ENDPOINT if endpoint == DEFAULT_ENDPOINT else api_origin
    file_sha256 = hashlib.sha256(image_bytes).hexdigest()
    preflight = {
        "uploaded_file": str(source),
        "file_size_bytes": len(image_bytes),
        "sha256": file_sha256,
        "image_format": image_format,
        "mime_type": mime_type,
        "image_dimensions": list(dimensions),
        "pixel_count": dimensions[0] * dimensions[1],
        "api_url": public_api_url,
        "api_origin": api_origin,
        "hand_drawn": hand_drawn,
    }
    if destination is not None:
        preflight["output_path"] = str(destination)

    if not confirm_upload:
        _refuse_upload(
            "Remote upload refused: set confirm_upload=true only after the user authorizes "
            "sending this exact image to the preflight DECIMER destination",
            preflight,
        )

    if approved_sha256 is not None:
        normalized_sha256 = approved_sha256.strip().lower()
        if len(normalized_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in normalized_sha256
        ):
            _refuse_upload("approved_sha256 must be a 64-character SHA-256 digest", preflight)
        if normalized_sha256 != file_sha256:
            _refuse_upload("approved_sha256 does not match the exact upload bytes", preflight)

    is_default_endpoint = endpoint == DEFAULT_ENDPOINT
    if approved_origin is not None:
        normalized_approval = _canonical_origin(approved_origin.strip(), approval=True)
        if normalized_approval != api_origin:
            _refuse_upload("approved_origin does not match the DECIMER destination", preflight)
    elif not is_default_endpoint:
        _refuse_upload(
            "Custom DECIMER destinations require approved_origin matching the preflight origin",
            preflight,
        )

    content_type, body = build_multipart_body(
        filename=source.name,
        mime_type=mime_type,
        image_bytes=image_bytes,
        hand_drawn=hand_drawn,
    )
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": content_type},
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = response.status
            _validate_final_url(response, endpoint, api_origin)
            response_bytes = response.read(max_response + 1)
            if len(response_bytes) > max_response:
                raise DecimerAPIError(
                    "DECIMER API response exceeds DECIMER_API_MAX_RESPONSE_BYTES"
                )
            response_text = response_bytes.decode("utf-8", errors="replace")
    except HTTPError as exc:
        read_error: OSError | ValueError | None = None
        try:
            try:
                detail_bytes = exc.read(max_response + 1)
            except (OSError, ValueError) as body_exc:
                detail_bytes = b""
                read_error = body_exc
        finally:
            try:
                exc.close()
            except OSError:
                pass
        if read_error is not None:
            detail = f"error body unavailable: {_sanitize_error_detail(read_error)}"
        elif len(detail_bytes) > max_response:
            detail = "response body exceeds DECIMER_API_MAX_RESPONSE_BYTES"
        else:
            detail = _sanitize_error_detail(
                detail_bytes.decode("utf-8", errors="replace")
            )
        raise DecimerAPIError(f"DECIMER API HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        detail = _sanitize_error_detail(exc.reason)
        raise DecimerAPIError(f"DECIMER API connection failed: {detail}") from exc
    except (OSError, TimeoutError) as exc:
        detail = _sanitize_error_detail(exc)
        raise DecimerAPIError(f"DECIMER API transport failed: {detail}") from exc

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        detail = _sanitize_error_detail(response_text)
        raise DecimerAPIError(
            f"DECIMER API returned non-JSON HTTP {status}: {detail}"
        ) from exc

    normalized = normalize_api_payload(payload)
    structures = [
        _validate_smiles(smiles, index)
        for index, smiles in enumerate(normalized["smiles"], start=1)
    ]
    warnings = []
    if len(structures) > 1:
        warnings.append(
            "The service segmented multiple candidates; inspect each result for false positives."
        )
    if any(item.get("valid") is False for item in structures):
        warnings.append("At least one returned SMILES failed RDKit validation.")

    result = {
        "ok": True,
        "source": "Steinbeck Lab Cheminformatics API / DECIMER",
        "api_url": public_api_url,
        "api_origin": api_origin,
        "api_contract": OPENAPI_URL,
        "uploaded_file": str(source),
        "file_size_bytes": len(image_bytes),
        "sha256": file_sha256,
        "image_format": image_format,
        "mime_type": mime_type,
        "image_dimensions": list(dimensions),
        "hand_drawn": hand_drawn,
        "reference": normalized["reference"],
        "structures": structures,
        "warnings": warnings,
        "raw_response": payload,
    }
    if destination is not None:
        result["output_path"] = str(destination)
        _atomic_write_json(destination, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_path")
    parser.add_argument("--hand-drawn", action="store_true")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output-path")
    parser.add_argument("--confirm-upload", action="store_true")
    parser.add_argument("--approved-sha256")
    parser.add_argument("--approved-origin")
    args = parser.parse_args()
    try:
        result = recognize_image(
            args.image_path,
            hand_drawn=args.hand_drawn,
            timeout_seconds=args.timeout,
            output_path=args.output_path,
            confirm_upload=args.confirm_upload,
            approved_sha256=args.approved_sha256,
            approved_origin=args.approved_origin,
        )
        exit_code = 0
    except DecimerAPIError as exc:
        result = exc.as_result()
        exit_code = 1
    except Exception as exc:
        result = {"ok": False, "error": _sanitize_error_detail(exc)}
        exit_code = 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
