# HCR Commercial Readiness Checklist

Status date: 2026-05-01

This is the working checklist for moving HCR from early alpha to commercial-grade product.

## Phase 1: Reliability

- [x] MCP stdio server responds correctly with framed JSON-RPC
- [x] MCP HTTP responder initializes correctly
- [x] CLI server startup path works from supported entrypoints
- [x] Basic diagnostics command exists: `hcr doctor`
- [x] Safer state/event persistence under concurrent access
- [ ] Daemon soak test for 24h+ on Windows/macOS/Linux
- [ ] Crash recovery verification for daemon/server restart
- [ ] State migration/version compatibility tests
- [ ] Concurrency/load tests for repeated MCP calls
- [ ] Automated regression suite in CI

## Phase 2: Installability

- [x] `setup.py` includes core runtime dependencies used by the code
- [x] VS Code extension can launch the local engine without relying on integrated terminal hacks
- [x] CLI can initialize or resume a fresh workspace without manual pre-setup
- [ ] Single supported install flow documented and tested end-to-end
- [ ] `pip install hcr` / editable install / extension flow tested on clean machines
- [ ] Optional provider setup guide with validation steps
- [ ] Installer or bootstrap script for non-technical users

## Phase 3: Product UX

- [x] Supportable diagnostics output exists
- [ ] Friendly remediation messages across all major failure paths
- [ ] Extension UI validated in real VS Code sessions
- [ ] Stable onboarding flow with minimal manual configuration
- [ ] `hcr explain` / `hcr doctor` surfaced clearly in docs and extension UX
- [ ] Remove stale/over-optimistic claims from README and docs

## Phase 4: Security and Operations

- [ ] Threat model for local state, daemon, and shared-state storage
- [ ] Sensitive data handling review for logs/state files
- [ ] Structured logging and support bundle strategy
- [ ] CI release process and versioning discipline
- [ ] Signed extension/release artifacts where applicable
- [ ] Backup/restore and data retention behavior defined

## Phase 5: Commercial Release Gate

- [ ] Clean install on a fresh machine succeeds without developer intervention
- [ ] Extension start/resume workflow works on supported OS targets
- [ ] LLM-enabled and heuristic-only modes both validated
- [ ] Error budget and support runbook defined
- [ ] Pricing/licensing packaging aligned with actual repo and extension metadata
- [ ] Documentation matches real product behavior

## Current Assessment

HCR is now in a stronger early-alpha state:

- MCP core is functioning
- server launch paths are materially better
- diagnostics exist
- VS Code integration is less brittle than before

HCR is not yet commercial grade because the remaining gaps are mostly in reproducibility, install flow, long-run reliability, and release/operations discipline rather than core feature existence.

## Immediate Next Recommended Work

1. Add CI smoke coverage for `hcr doctor`, `hcr resume`, and MCP tool regression.
2. Define one canonical install path and test it on a clean machine.
3. Run daemon/server soak tests and fix restart/data-corruption issues.
4. Remove inaccurate claims from README and extension docs.
