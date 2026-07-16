#!/usr/bin/env python3

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence, TextIO
from urllib.parse import urlsplit


class SkillError(Exception):
    """A user-actionable Zabbix API failure."""


@dataclass(frozen=True)
class ApiConfig:
    url: str
    token: str | None
    ca_file: str | None


def load_config(require_token: bool, env: Mapping[str, str]) -> ApiConfig:
    url = env.get("ZABBIX_API_URL", "").strip()
    if not url:
        raise SkillError("ZABBIX_API_URL is required")

    try:
        parsed_url = urlsplit(url)
    except ValueError:
        raise SkillError("ZABBIX_API_URL must be a valid URL") from None
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise SkillError("ZABBIX_API_URL must be a full http or https URL")
    if parsed_url.username is not None or parsed_url.password is not None:
        raise SkillError("ZABBIX_API_URL must not contain credentials")
    try:
        hostname = parsed_url.hostname
        parsed_url.port
    except ValueError:
        raise SkillError("ZABBIX_API_URL must be a valid URL") from None
    if hostname is None:
        raise SkillError("ZABBIX_API_URL must be a valid URL")

    token = env.get("ZABBIX_API_TOKEN", "").strip() or None
    if require_token and token is None:
        raise SkillError("ZABBIX_API_TOKEN is required")

    ca_file = env.get("ZABBIX_CA_FILE", "").strip() or None
    if ca_file is not None and not (
        os.path.isfile(ca_file) and os.access(ca_file, os.R_OK)
    ):
        raise SkillError("ZABBIX_CA_FILE must name a readable file")

    return ApiConfig(url=url, token=token, ca_file=ca_file)


def build_ssl_context(config: ApiConfig) -> ssl.SSLContext | None:
    if urlsplit(config.url).scheme == "https":
        return ssl.create_default_context(cafile=config.ca_file)
    return None


def load_json_params(
    path: str | None, use_stdin: bool, stdin: TextIO
) -> dict[str, object]:
    if path is not None and use_stdin:
        raise SkillError("use only one parameter input source")
    if path is None and not use_stdin:
        return {}

    source = path if path is not None else "standard input"
    try:
        if path is not None:
            with open(path, encoding="utf-8") as params_file:
                params = json.load(params_file)
        else:
            params = json.load(stdin)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise SkillError(f"could not load JSON parameters from {source}") from None

    if not isinstance(params, dict):
        raise SkillError(f"JSON parameters from {source} must be an object")
    return params


class ZabbixClient:
    def __init__(self, config: ApiConfig):
        self.config = config
        self._next_id = 1

    def call(self, method: str, params: object, authenticated: bool) -> object:
        request_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }
        if authenticated:
            if self.config.token is None:
                raise SkillError("ZABBIX_API_TOKEN is required")
            payload["auth"] = self.config.token

        request = urllib.request.Request(
            self.config.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json-rpc"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=30,
                context=build_ssl_context(self.config),
            ) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            error.close()
            raise SkillError(f"Zabbix API returned HTTP {error.code}") from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise SkillError("Zabbix API request timed out") from None
            raise SkillError("could not connect to Zabbix API") from None
        except TimeoutError:
            raise SkillError("Zabbix API request timed out") from None
        except OSError:
            raise SkillError("could not connect to Zabbix API") from None

        try:
            response_payload = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise SkillError("Zabbix API returned malformed JSON") from None

        if not isinstance(response_payload, dict):
            raise SkillError("Zabbix API returned an invalid JSON-RPC response")
        if response_payload.get("jsonrpc") != "2.0":
            raise SkillError("Zabbix API returned an invalid JSON-RPC version")
        if response_payload.get("id") != request_id:
            raise SkillError("Zabbix API returned a mismatched response ID")
        if "error" in response_payload:
            raise SkillError("Zabbix API returned a JSON-RPC error")
        if "result" not in response_payload:
            raise SkillError("Zabbix API response is missing result")
        return response_payload["result"]

    def version(self) -> str:
        return self.call("apiinfo.version", {}, authenticated=False)


def current_problem_params(extra: Mapping[str, object]) -> dict[str, object]:
    params: dict[str, object] = {
        "output": "extend",
        "recent": False,
        "sortfield": ["eventid"],
        "sortorder": "DESC",
        "selectAcknowledges": "extend",
        "selectTags": "extend",
        "selectSuppressionData": "extend",
    }
    params.update(extra)
    params["recent"] = False
    return params


def parse_timestamp(value: str) -> datetime:
    iso_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError:
        raise SkillError("timestamp must be valid ISO-8601") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SkillError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def historical_problem_params(
    since: str,
    until: str | None,
    extra: Mapping[str, object],
    now: datetime | None = None,
) -> dict[str, object]:
    since_time = parse_timestamp(since)
    if until is not None:
        until_time = parse_timestamp(until)
    else:
        until_time = now if now is not None else datetime.now(timezone.utc)
        if until_time.tzinfo is None or until_time.utcoffset() is None:
            raise SkillError("current time must include a timezone")
        until_time = until_time.astimezone(timezone.utc)
    if since_time >= until_time:
        raise SkillError("--since must be before --until")

    params: dict[str, object] = {
        "sortfield": ["clock", "eventid"],
        "sortorder": "DESC",
    }
    params.update(extra)
    params.update(
        {
            "source": 0,
            "object": 0,
            "value": 1,
            "time_from": int(since_time.timestamp()),
            "time_till": int(until_time.timestamp()),
        }
    )
    return params


def host_query_params(extra: Mapping[str, object]) -> dict[str, object]:
    params: dict[str, object] = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": [
            "interfaceid",
            "type",
            "main",
            "useip",
            "ip",
            "dns",
            "port",
        ],
    }
    params.update(extra)
    return params


def check_supported_version(version: str) -> str | None:
    components = version.split(".") if isinstance(version, str) else []
    if len(components) < 3 or not all(
        component.isascii() and component.isdecimal()
        for component in components[:3]
    ):
        raise SkillError("Zabbix API returned a malformed version string")
    try:
        major, minor, _patch = (int(component) for component in components[:3])
    except ValueError:
        raise SkillError("Zabbix API returned a malformed version string") from None
    if (major, minor) < (5, 4):
        raise SkillError("Zabbix 5.4 or newer is required")
    if (major, minor) > (5, 4):
        return f"Zabbix {version} compatibility is not verified"
    return None


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("version")

    problems_parser = subparsers.add_parser("problems")
    problems_subparsers = problems_parser.add_subparsers(
        dest="problems_command", required=True
    )
    current_parser = problems_subparsers.add_parser("current")
    current_parser.add_argument("--params-file")
    history_parser = problems_subparsers.add_parser("history")
    history_parser.add_argument("--since", required=True)
    history_parser.add_argument("--until")
    history_parser.add_argument("--params-file")

    hosts_parser = subparsers.add_parser("hosts")
    hosts_subparsers = hosts_parser.add_subparsers(dest="hosts_command", required=True)
    hosts_get_parser = hosts_subparsers.add_parser("get")
    hosts_get_parser.add_argument("--params-file")

    args = parser.parse_args(argv)

    try:
        environment = os.environ if env is None else env
        require_token = args.command != "version"
        config = load_config(require_token=require_token, env=environment)
        client = ZabbixClient(config)
        if args.command == "version":
            result = client.version()
        elif args.command == "problems":
            extra = load_json_params(args.params_file, False, sys.stdin)
            if args.problems_command == "current":
                method = "problem.get"
                params = current_problem_params(extra)
            else:
                method = "event.get"
                params = historical_problem_params(args.since, args.until, extra)
            version = client.version()
            warning = check_supported_version(version)
            result = client.call(method, params, authenticated=True)
        else:
            extra = load_json_params(args.params_file, False, sys.stdin)
            version = client.version()
            warning = check_supported_version(version)
            result = client.call(
                "host.get", host_query_params(extra), authenticated=True
            )

        if args.command == "version":
            warning = check_supported_version(result)
        print(json.dumps(result, indent=2))
        if warning is not None:
            print(f"warning: {warning}", file=sys.stderr)
        return 0
    except SkillError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
