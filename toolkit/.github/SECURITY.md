# Security Policy

## Supported versions

Security fixes are provided for the latest community release and the current
`main` branch.

## Reporting a vulnerability

Use the repository's private GitHub Security Advisory reporting feature. Do not
open a public issue for credentials, arbitrary file access, unsafe archive
handling, remote execution, or private chemistry data exposure.

Reports should include the affected version, reproduction steps, impact, and a
minimal non-sensitive fixture. Please do not include licensed ChemDraw,
ChemScript, Office, or proprietary experiment files.

## Native software

ChemDraw COM, ChemScript, Office automation, OCR engines, and optional model
runtimes execute with the permissions of the current Windows user. Process
separation can limit stalled calls, but it does not create an operating-system
security sandbox.

