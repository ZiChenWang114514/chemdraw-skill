# DECIMER 2 API Reference

Verified against the live service and official sources on 2026-07-11.

## Two Different APIs

### DECIMER 2.8.0 Python API

The official PyPI package exposes a local Python function:

```python
from DECIMER import predict_SMILES

smiles = predict_SMILES(
    image_input="structure.png",
    confidence=False,
    hand_drawn=False,
)
```

Signature:

```text
predict_SMILES(image_input, confidence=False, hand_drawn=False) -> str
```

`image_input` accepts an image path or NumPy array. This is a local inference API and requires the DECIMER model archives. It is not an HTTP call.

Official sources:

- Package: https://pypi.org/project/decimer/
- Function documentation: https://decimer-image-transformer.readthedocs.io/en/latest/DECIMER.html

### Remote Steinbeck Lab API

This is the endpoint behind `cdx.py decimer`; call that command instead of posting yourself, because it adds the preflight, image size limits, the offline refusal and response checks. The contract is listed for reference:

```text
POST https://api.naturalproducts.net/latest/ocsr/process-upload
Content-Type: multipart/form-data
Accept: application/json
```

Multipart fields:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `file` | binary image | yes | Chemical structure depiction image |
| `hand_drawn` | boolean text | no | `true` for sketches; default `false` |

No authentication scheme is declared by the current OpenAPI document.

```bash
curl -X POST \
  "https://api.naturalproducts.net/latest/ocsr/process-upload" \
  -H "Accept: application/json" \
  -F "file=@structure.png;type=image/png" \
  -F "hand_drawn=false"
```

Official live contract and documentation:

- OpenAPI 3.1: https://api.naturalproducts.net/latest/openapi.json
- Swagger UI: https://api.naturalproducts.net/latest/docs

## Response Handling

The OpenAPI schema currently declares:

```json
{
  "message": "Success",
  "reference": "string",
  "smiles": "string"
}
```

The live service returned this shape during verification:

```json
{
  "reference": null,
  "smiles": ["CC(=O)OC1=CC=CC=C1C(=O)O", "[Cr]"]
}
```

Therefore clients must accept `smiles` as either a string or a list of strings, and `reference` as a string or null. The extra `[Cr]` prediction came from a labeled aspirin test image and demonstrates that segmentation can produce false-positive candidates. RDKit validity is necessary but not sufficient for accepting a result.

The skill client normalizes output to:

```json
{
  "ok": true,
  "source": "Steinbeck Lab Cheminformatics API / DECIMER",
  "structures": [
    {
      "index": 1,
      "smiles": "...",
      "valid": true,
      "formula": "...",
      "molecular_weight": 0.0
    }
  ],
  "warnings": []
}
```

## Skill Usage

```bash
cdx.py decimer crop.png --out crop-decimer.json          # upload and recognize (default endpoint)
cdx.py decimer sketch.png --hand-drawn
cdx.py decimer crop.png --preflight                      # no upload: size, format, sha256, origin
```

The tool behind it is `extract_structures_via_decimer_api` (signature in [mcp-signatures.md](mcp-signatures.md)). Upload follows the rule in SKILL.md: task images and their crops go up without asking; ask once for unpublished or confidential sources; never upload when the user wants offline work.

The built-in endpoint needs nothing else. For a **custom endpoint**, set `DECIMER_API_URL` (HTTPS) and pass its origin; to pin the exact bytes, take `sha256` from a `--preflight` run:

```bash
DECIMER_API_URL=https://ocsr.example.org/process cdx.py call extract_structures_via_decimer_api --json '{"image_path": "<abs>/crop.png", "confirm_upload": true, "approved_origin": "https://ocsr.example.org", "approved_sha256": "<sha256 from --preflight>"}'
```

In PowerShell, set the variable first (`$env:DECIMER_API_URL = "https://ocsr.example.org/process"`) and pass the arguments with `--args file.json`. `cdx.py decimer` has no origin option, so while `DECIMER_API_URL` names another server its uploads are refused ("Custom DECIMER destinations require approved_origin"); use the `call` form above. The preflight `sha256` is computed over the bytes actually sent: the file name is replaced by `image.<ext>` and embedded metadata (EXIF, PNG text) is removed first, as the preflight's `upload_filename` and `metadata_removed` fields show.

Limits: `DECIMER_API_MAX_IMAGE_BYTES` (25 MiB), `DECIMER_API_MAX_IMAGE_PIXELS` (40,000,000), `DECIMER_API_MAX_RESPONSE_BYTES` (2 MiB).

## Diagnosing failed requests

Expected failures (HTTP status, connection errors, invalid images, refused upload) come back as `ok=false` with a readable `error`. For a bare `tool_execution_failed`, read the worker log named by its `error_id` (`cdx.py doctor --paths`).

HTTP 502/503/504 is a gateway or service problem, not a local installation problem. Retry the same image at most twice with a short pause, then report the failure. Do not switch endpoints, disable TLS checks, or raise the timeout to work around it. Reaching the OpenAPI page only shows the service is reachable; a successful recognition POST shows it works.

A successful response says nothing about accuracy: check segmentation and every predicted structure against the image.

## Notes

- The client follows only same-origin HTTPS redirects and decodes the image locally before upload; the MIME type comes from the decoded format.
- The public contract states no rate limit or retention policy.
- `https://decimer.ai` is a web application, not this REST endpoint.
- The `/latest` alias can change; re-read the live OpenAPI document if requests start failing or fields change.
