# Zabbix API Skill Design

**Date:** 2026-07-15
**Status:** Approved design; pending written-spec review

## Objective

Create a personal Pi skill for interacting with Zabbix through its JSON-RPC API. The first version must support Zabbix 5.4, authenticate with an API token, inspect current and historical problems, query hosts, and safely create or update hosts.

The implementation will be intentionally narrow: it will cover the requested problem and host operations without becoming a general-purpose Zabbix SDK.

## Requirements

### Environment

- `ZABBIX_API_URL` is required for live operations and contains the complete endpoint, for example `https://zabbix.example.com/api_jsonrpc.php`.
- `ZABBIX_API_TOKEN` is required for authenticated live operations.
- `ZABBIX_CA_FILE` is optional and identifies a custom CA bundle for HTTPS verification.
- The helper uses Python 3 and its standard library only.

### Compatibility

- Requests must use the Zabbix 5.4 JSON-RPC format.
- Authenticated requests place `ZABBIX_API_TOKEN` in the JSON-RPC `auth` field, as required for Zabbix 5.4 API-token compatibility.
- The helper calls `apiinfo.version` before authenticated live operations.
- Zabbix 5.4 is accepted and tested.
- Versions older than 5.4 are rejected.
- Newer versions are allowed with a compatibility warning on stderr.

### Supported operations

- Report the server API version.
- Retrieve active problems.
- Retrieve historical problem events over a bounded time range.
- Query hosts.
- Preview and create hosts from complete Zabbix-compatible JSON parameters.
- Preview and update hosts from complete Zabbix-compatible JSON parameters.

Host deletion and arbitrary JSON-RPC methods are outside the first version.

## Architecture

Create the following package:

```text
skills/zabbix-api/
├── SKILL.md
├── scripts/
│   └── zabbix_api.py
├── references/
│   └── zabbix-5.4-api.md
└── tests/
    ├── scenarios.md
    └── test_zabbix_api.py
```

### `SKILL.md`

The skill document defines when to load the skill, the safety policy, the standard read and mutation workflows, command examples, output interpretation, and common mistakes. It directs agents to the bundled Zabbix 5.4 reference for operation-specific details.

### `scripts/zabbix_api.py`

A standard-library Python CLI owns configuration loading, TLS setup, JSON-RPC request construction, version enforcement, time parsing, mutation previews, and response/error handling.

Planned command surface:

```text
zabbix_api.py version
zabbix_api.py problems current [--params-file PATH]
zabbix_api.py problems history --since TIME [--until TIME] [--params-file PATH]
zabbix_api.py hosts get [--params-file PATH]
zabbix_api.py hosts create (--params-file PATH | --params-stdin) [--apply --confirm-digest SHA256]
zabbix_api.py hosts update (--params-file PATH | --params-stdin) [--apply --confirm-digest SHA256]
```

`TIME` accepts ISO-8601 timestamps with `Z` or an explicit UTC offset. `--until` defaults to the current time. Naive local timestamps are rejected.

Parameter files contain the complete JSON-RPC `params` value, not an outer JSON-RPC envelope. Query parameter files add or override non-safety defaults. Historical query parameters cannot override `source`, `object`, `value`, `time_from`, or `time_till`; those values are derived by the helper to preserve problem-event semantics and bounded history.

Mutation parameter input may be a JSON object or a nonempty array of objects, matching Zabbix batch method conventions. The helper performs structural checks only; Zabbix remains authoritative for complete host-schema validation.

### `references/zabbix-5.4-api.md`

The reference records the exact 5.4 methods used, their fixed/default parameters, authentication convention, important returned fields, and links to official Zabbix 5.4 documentation. It avoids copying the full upstream API reference.

## Operation behavior

### Version

`version` calls unauthenticated `apiinfo.version` and prints the version result. It requires `ZABBIX_API_URL` but not `ZABBIX_API_TOKEN`.

### Current problems

`problems current` calls `problem.get`. Defaults set `recent` to false, sort newest first, use `output: extend`, and request acknowledgments, tags, and suppression data through the corresponding Zabbix 5.4 selections.

Optional query parameters may narrow results by host, group, severity, acknowledgment, or other valid `problem.get` filters. The helper must not silently turn the operation into a historical query.

### Historical problems

`problems history` calls `event.get` with trigger problem-event semantics:

- `source = 0`
- `object = 0`
- `value = 1`
- `time_from` derived from required `--since`
- `time_till` derived from `--until`, defaulting to now
- newest events first

This method is used because `problem.get` does not retain arbitrarily old resolved problems. Optional parameters may add host, group, severity, acknowledgment, and output filters but cannot remove the bounded interval or change the event type.

### Host queries

`hosts get` calls `host.get`. Conservative defaults return host identity, status, and interface information. A query parameter file can request additional filters and related objects such as groups, templates, inventory, or macros.

Agents should prefer targeted filters and reasonable limits instead of retrieving the entire environment when the request is narrow.

### Host creation and updates

`hosts create` maps to `host.create`; `hosts update` maps to `host.update`. Both are dry-run operations unless explicitly applied.

Dry-run behavior:

1. Parse the supplied JSON.
2. Validate its top-level structure.
3. Canonicalize the method and parameters.
4. Print the exact method and parameters without authentication.
5. Print a SHA-256 digest of that canonical preview.
6. Exit without making a network request.

Apply behavior requires both `--apply` and `--confirm-digest SHA256`. The helper recalculates the digest and rejects the operation if it differs. The skill requires the agent to show the exact preview and expected impact to the user and receive explicit approval before running the apply command.

A general request to manage Zabbix or permission to perform read operations is not approval for a mutation. Approval applies only to the previewed method and payload.

## Data flow

For a read operation:

1. Parse CLI arguments.
2. Validate the URL, token, optional CA file, times, and parameter input as applicable.
3. Call `apiinfo.version` and enforce the version policy.
4. Construct a JSON-RPC 2.0 request with a unique request ID.
5. Add the API token to `auth` for authenticated calls.
6. Send the POST request with certificate verification enabled for HTTPS.
7. Validate the HTTP and JSON-RPC response.
8. Print the `result` as formatted JSON on stdout.

For a dry-run mutation, configuration and network access are not required. For an applied mutation, the same live-operation flow runs only after digest confirmation succeeds.

## Security and safety

- Never print, log, persist, or include `ZABBIX_API_TOKEN` in previews or errors.
- Never read authentication from command-line arguments, where it could appear in process listings or shell history.
- Verify HTTPS certificates by default.
- Use `ZABBIX_CA_FILE` when a private CA is required.
- Do not implement an insecure TLS bypass option.
- Permit explicit `http://` endpoints for trusted internal deployments, while the skill warns that transport is unencrypted.
- Do not create temporary files containing the API token.
- Do not add host deletion or generic arbitrary-method execution in this version.
- Require exact payload approval for every create or update operation.

## Output and error handling

Successful commands print machine-readable, indented JSON to stdout. Warnings and diagnostics go to stderr. Failures return a nonzero exit status.

Errors must be concise and actionable for:

- Missing or empty environment variables.
- Invalid endpoint schemes or malformed URLs.
- Missing or unreadable CA and parameter files.
- Invalid JSON or parameter shape.
- Missing timezone information or reversed history ranges.
- HTTP failures and connection timeouts.
- Invalid or non-JSON responses.
- JSON-RPC error objects.
- Missing JSON-RPC results or mismatched response IDs.
- Unsupported Zabbix versions.
- Missing, malformed, or mismatched mutation digests.

Error text must not include the token, request headers, or an authenticated raw request body.

## Testing strategy

### Automated helper tests

Use Python `unittest` and a local fake JSON-RPC HTTP server. Tests must not require external packages, a real Zabbix server, or a real API token.

Coverage includes:

- Environment and endpoint validation.
- Optional custom CA handling.
- Unauthenticated version requests.
- Zabbix 5.4 token placement in the JSON-RPC `auth` field.
- Acceptance of 5.4, rejection below 5.4, and warnings above 5.4.
- `problem.get` request construction for current problems.
- `event.get` problem-event filters and bounded history ranges.
- ISO-8601 conversion, default `--until`, and invalid ranges.
- `host.get` defaults and parameter overrides.
- Mutation parsing, canonical preview, and digest stability.
- Proof that dry-run mutation performs no network request.
- Successful apply with a matching digest.
- Rejection of changed payloads and absent confirmations.
- HTTP, malformed response, response-ID, and JSON-RPC failures.
- Token redaction from stdout and stderr on failures.

Tests for implementation behavior follow test-first development: each behavior is first demonstrated by a failing test, then implemented minimally.

### Skill scenarios

Before writing `SKILL.md`, baseline scenarios run without the skill and document failures. The same scenarios then run with the skill and verify that an agent:

- Uses `problem.get` for current problems.
- Uses bounded `event.get` for older resolved problems.
- Reads the token only from `ZABBIX_API_TOKEN`.
- Does not expose the token while diagnosing errors.
- Uses targeted host queries.
- Previews create/update parameters and waits for exact approval.
- Refuses apply when the payload differs from the approved digest.

`tests/scenarios.md` records the scenarios, baseline observations, and post-skill results.

## Acceptance criteria

The skill is complete when:

1. Pi discovers `zabbix-api` from valid frontmatter.
2. All helper tests pass using only Python 3's standard library.
3. Verification scenarios show correct current/history method selection and mutation approval behavior.
4. A fake Zabbix 5.4 endpoint confirms that authenticated calls use the JSON-RPC `auth` field.
5. Current problems, bounded historical problem events, and host queries produce valid JSON results.
6. Host creation and updates cannot be applied without a matching approved digest.
7. No tested output or error path exposes `ZABBIX_API_TOKEN`.
8. The implementation and tests touch only files needed for this skill.
