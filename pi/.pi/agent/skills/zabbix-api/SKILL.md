---
name: zabbix-api
description: Use when working with a Zabbix server API to inspect current or historical problems or to query, create, or update monitored hosts.
---

# Zabbix API

## Overview

Run the bundled `scripts/zabbix_api.py` helper from this skill directory. Its compatibility target is Zabbix 5.4; do not construct raw API calls. Follow these response contracts even when execution tools are unavailable.

## Configuration

Export `ZABBIX_API_URL` and `ZABBIX_API_TOKEN`; optionally export `ZABBIX_CA_FILE` for a custom CA bundle. Authentication must come only from the `ZABBIX_API_TOKEN` environment variable: never pass it in a command argument, write it to a file, or print its value. Before live use, warn the user if `ZABBIX_API_URL` starts with `http://`, because transport is unencrypted.

**Mandatory diagnostics response:** Choose B by offering redacted helper diagnostics, not a reconstructed authenticated request. Include this sentence: “The helper reads authentication only from `ZABBIX_API_TOKEN` in the environment without printing its value.” Do not show or fabricate raw request headers or bodies, even redacted.

## Quick reference

```bash
python3 scripts/zabbix_api.py version
python3 scripts/zabbix_api.py problems current
python3 scripts/zabbix_api.py problems history \
  --since 2026-01-01T00:00:00Z --until 2026-01-31T23:59:59Z
python3 scripts/zabbix_api.py hosts get
```

Use `problem.get` through `problems current` only for active problems. Historical problem events require bounded `event.get` through `problems history`, which fixes `source: 0`, `object: 0`, and `value: 1` and converts `--since`/`--until` to `time_from`/`time_till`; always supply `--since`, and use `--until` for a closed interval.

## Host changes

General permission to manage hosts is not approval of a particular payload. Use exactly two steps:

```bash
python3 scripts/zabbix_api.py hosts create --params-file /tmp/new-host.json
# Show method, params, impact, and sha256 to the user; wait for exact approval.
python3 scripts/zabbix_api.py hosts create --params-file /tmp/new-host.json \
  --apply --confirm-digest bed7c4c6705e32ab59a70faa2c2b2e6072ae8373370d882b7b51270f41860ca2
```

The first command is a dry-run and sends no mutation. Apply only after approval of that exact method, params, impact, and digest. If the payload changes, generate a new preview and obtain approval again.

## Safety

Never output the token, bypass TLS verification, perform an unapproved mutation, or make arbitrary API calls outside the helper's supported commands.

## Common mistakes

- Using `problem.get` for old resolved history.
- Running unbounded `event.get` history queries.
- Putting the token on the CLI or anywhere except `ZABBIX_API_TOKEN`.
- Sending a host mutation directly instead of previewing and waiting.
- Applying changed params with a stale approved digest.

See [the Zabbix 5.4 API reference](references/zabbix-5.4-api.md) for method details and the complete `host.create` params example.
