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

Use this endpoint for online recognition:

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

Use the MCP tool `extract_structures_via_decimer_api`. Its generated, authoritative
signature is in [mcp-signatures.md](mcp-signatures.md); this guide maintains only the
privacy decisions and failure behavior.

For image-recognition tasks, call with `confirm_upload=true` directly. Do not ask a
separate upload-authorization question. Respect explicit local/offline or no-upload
requests. A no-upload preflight is optional: when a caller explicitly sets
`confirm_upload=false`, the MCP wrapper refuses the upload and returns
an `ok=false` result containing a `preflight` object with the resolved local path, byte
size, SHA-256 digest, decoded format and MIME type, dimensions, pixel count, hand-drawn
flag, and upload origin. Direct Python calls raise `DecimerUploadRefused` with the same
preflight available on the exception.

The normal recognition workflow uses `confirm_upload=true`. The built-in endpoint needs no
additional origin argument. `approved_sha256`, when supplied, must match the exact bytes
used to build the upload. Any custom `DECIMER_API_URL`, including another path on the
default origin, additionally requires `approved_origin` to match its canonical HTTPS
origin.

The CLI equivalent is:

```powershell
$skillRoot = '<absolute path to the installed chemdraw Skill>'
$runtime = & python (Join-Path $skillRoot 'scripts\runtime_discovery.py') --json |
  ConvertFrom-Json
& $runtime.python.path (Join-Path $runtime.skill_root.path 'scripts\decimer_api.py') `
  C:\path\to\structure.png `
  --confirm-upload `
  --approved-sha256 <digest> `
  --approved-origin https://custom.example
```

Omit `--approved-origin` only for the exact built-in endpoint. Omitting
`--confirm-upload` prints a refusal result with preflight metadata and performs no
network request.

Environment overrides:

- `DECIMER_API_URL`: custom API endpoint; defaults to the official upload endpoint above. It must use HTTPS, contain no URL userinfo, query, or fragment, and its canonical origin must be supplied as `approved_origin`.
- `DECIMER_API_MAX_IMAGE_BYTES`: local upload-size guard; defaults to 25 MiB.
- `DECIMER_API_MAX_IMAGE_PIXELS`: decoded pixel-count guard; defaults to 40,000,000 pixels.
- `DECIMER_API_MAX_RESPONSE_BYTES`: response-size guard; defaults to 2 MiB.

## Diagnosing failed requests

The MCP wrapper returns expected client failures as `ok=false` with a readable
`error`, including HTTP status, connection failures, invalid images, and upload
refusals. Direct Python calls still raise `DecimerAPIError`. Unexpected programming
errors remain worker failures with a local diagnostic log.

For HTTP 502, 503, or 504, inspect the network path and service availability before
changing the installation. A gateway error alone cannot distinguish a local proxy
failure from a remote gateway failure. A successful GET of the OpenAPI document
checks reachability only; recovery requires a successful recognition POST with an
task image. Retry the same image and destination at most twice, with a short
pause, then report the persistent failure. Do not switch upload destinations or
disable TLS checks to work around an outage. Increasing the timeout does not fix an
HTTP 502 response.

When a client still shows only `tool_execution_failed`, use its `error_id` to read
the worker log described in [operations.md](operations.md). Confirm the active
Python runtime and package path: Skill compatibility scripts delegate to the
installed `cdxml_toolkit.mcp_runtime` package, so updating documentation alone does
not update the MCP implementation. Verify the tool again through the active MCP
connection after applying a runtime fix.

Successful recognition establishes service availability, not chemical accuracy.
Review segmentation and each predicted structure against the input image.

## Boundaries

- Remote recognition sends task images and relevant crops to the DECIMER service by default, without a separate confirmation prompt. Honor explicit local/offline or no-upload requests. This default does not cover unrelated files or arbitrary destinations.
- Before reading image contents, the client stats the file and rejects oversized or non-regular inputs. The read itself is also bounded so file growth cannot bypass the byte limit.
- The client decodes the exact selected bytes through `BytesIO`, checks dimensions and the configured pixel cap before full image loading, treats Pillow decompression-bomb warnings as errors, and derives MIME from the decoded format rather than the filename extension.
- Only same-origin HTTPS redirects are followed. HTTPS downgrades, cross-origin redirects, and a mismatched or downgraded final response URL are rejected.
- Normal and HTTP-error response reads are bounded. Custom endpoint metadata is reduced to its approved origin, and URL credentials, paths, and query values are not echoed in transport or response errors.
- JSON output uses an atomic same-directory install that refuses existing or race-created destinations. The serialized file is the same result object returned to the caller.
- The public contract does not state a rate limit or retention guarantee. Do not infer either.
- `https://decimer.ai` is a CSRF-protected Laravel web application, not the REST endpoint used here. Its current official source has no DECIMER route in `routes/api.php`.
- The `/latest` alias can change with future deployments. Re-read the live OpenAPI document when requests begin failing or response fields change.
