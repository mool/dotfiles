#!/usr/bin/env python3

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Sequence
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
    args = parser.parse_args(argv)

    try:
        config = load_config(require_token=False, env=os.environ if env is None else env)
        if args.command == "version":
            result = ZabbixClient(config).version()
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
