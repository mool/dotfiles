import contextlib
import importlib.util
import http.client
import io
import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).parents[1] / "scripts" / "zabbix_api.py"


def load_module():
    spec = importlib.util.spec_from_file_location("zabbix_api", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class JsonRpcHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        self.server.requests.append(payload)
        reply = self.server.responder(payload)
        status, response = reply[:2]
        body = response if isinstance(response, bytes) else json.dumps(response).encode()
        content_length = reply[2] if len(reply) == 3 else len(body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(content_length))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@contextlib.contextmanager
def fake_zabbix(responder):
    server = ThreadingHTTPServer(("127.0.0.1", 0), JsonRpcHandler)
    server.requests = []
    server.responder = responder
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}/api_jsonrpc.php"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def rpc_result(payload, result):
    return 200, {"jsonrpc": "2.0", "result": result, "id": payload["id"]}


def run_cli(*args, env, input_text=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


class ArgumentParsingSecrecyTests(unittest.TestCase):
    sentinel = "SENSITIVE-ARGPARSE-TOKEN-7f4d"

    def assert_sanitized_parse_error(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(self.sentinel, result.stdout)
        self.assertNotIn(self.sentinel, result.stderr)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertLessEqual(len(result.stderr.splitlines()), 4)

    def test_invalid_subcommand_does_not_echo_configured_token(self):
        result = run_cli(
            "hosts",
            self.sentinel,
            env={**os.environ, "ZABBIX_API_TOKEN": self.sentinel},
        )

        self.assert_sanitized_parse_error(result)

    def test_unrecognized_extra_argument_does_not_echo_configured_token(self):
        result = run_cli(
            "version",
            self.sentinel,
            env={**os.environ, "ZABBIX_API_TOKEN": self.sentinel},
        )

        self.assert_sanitized_parse_error(result)


class ParameterInputTests(unittest.TestCase):
    def test_loads_json_object_from_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "params.json"
            path.write_text('{"hostids": ["10105"]}', encoding="utf-8")
            params = module.load_json_params(str(path), False, None)
        self.assertEqual(params, {"hostids": ["10105"]})

    def test_rejects_malformed_json_without_echoing_contents(self):
        module = load_module()
        secret_contents = '{"sentinel-secret": invalid}'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "params.json"
            path.write_text(secret_contents, encoding="utf-8")
            with self.assertRaisesRegex(module.SkillError, str(path)) as raised:
                module.load_json_params(str(path), False, None)
        self.assertNotIn(secret_contents, str(raised.exception))

    def test_rejects_non_object_query_value_and_names_stdin(self):
        module = load_module()
        with self.assertRaisesRegex(module.SkillError, "standard input"):
            module.load_json_params(None, True, io.StringIO('["not-an-object"]'))

    def test_rejects_file_and_stdin_together(self):
        module = load_module()
        with self.assertRaisesRegex(module.SkillError, "only one"):
            module.load_json_params("params.json", True, io.StringIO("{}"))

    def test_rejects_non_json_numeric_constants(self):
        module = load_module()
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaisesRegex(module.SkillError, "JSON"):
                    module.load_json_params(
                        None,
                        True,
                        io.StringIO('{"value": ' + constant + "}"),
                    )


class MutationShapeDigestTests(unittest.TestCase):
    def test_mutation_params_accept_object_or_nonempty_object_list(self):
        module = load_module()
        params = {"host": "edge-1"}
        batch_params = [{"host": "edge-1"}, {"host": "edge-2"}]
        self.assertIs(module.validate_mutation_params(params), params)
        self.assertIs(module.validate_mutation_params(batch_params), batch_params)

    def test_mutation_params_reject_invalid_shapes(self):
        module = load_module()
        for params in ([], "edge-1", [{"host": "edge-1"}, "edge-2"]):
            with self.subTest(params=params):
                with self.assertRaises(module.SkillError):
                    module.validate_mutation_params(params)

    def test_mutation_digest_is_stable_and_covers_method_and_params(self):
        module = load_module()
        params = {"groups": [{"groupid": "2"}], "host": "edge-1"}
        self.assertEqual(
            module.canonical_mutation("host.create", params),
            b'{"method":"host.create","params":{"groups":[{"groupid":"2"}],"host":"edge-1"}}',
        )
        self.assertEqual(
            module.mutation_digest("host.create", params),
            "79a1738c95fcc3be720fabc75b5bb0bf275250b6ccbef2a99b4e0bfd953487ec",
        )

    def test_canonical_mutation_rejects_non_json_numeric_constants(self):
        module = load_module()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(module.SkillError, "JSON"):
                    module.canonical_mutation("host.create", {"value": value})


class MutationDryRunTests(unittest.TestCase):
    def test_host_create_file_previews_without_live_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(
                '{"groups": [{"groupid": "2"}], "host": "edge-1"}',
                encoding="utf-8",
            )
            result = run_cli(
                "hosts", "create", "--params-file", str(path), env={}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "dry_run": True,
                "method": "host.create",
                "params": {
                    "groups": [{"groupid": "2"}],
                    "host": "edge-1",
                },
                "sha256": (
                    "79a1738c95fcc3be720fabc75b5bb0bf"
                    "275250b6ccbef2a99b4e0bfd953487ec"
                ),
            },
        )

    def test_host_update_stdin_previews_without_network_or_token_exposure(self):
        sentinel = "SENSITIVE-ZABBIX-TOKEN"
        params = {"hostid": "10105", "name": "Edge One"}
        with fake_zabbix(lambda payload: rpc_result(payload, {})) as (server, url):
            result = run_cli(
                "hosts",
                "update",
                "--params-stdin",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": sentinel,
                },
                input_text=json.dumps(params),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "dry_run": True,
                "method": "host.update",
                "params": params,
                "sha256": load_module().mutation_digest("host.update", params),
            },
        )
        self.assertEqual(server.requests, [])
        self.assertNotIn(sentinel, result.stdout)
        self.assertNotIn(sentinel, result.stderr)

    def test_preview_rejects_configured_token_in_exact_params_without_live_config(self):
        sentinel = "SENSITIVE-ZABBIX-TOKEN"
        result = run_cli(
            "hosts",
            "create",
            "--params-stdin",
            env={"ZABBIX_API_TOKEN": sentinel},
            input_text=json.dumps(
                {"host": "edge-1", "macros": [{"value": sentinel}]}
            ),
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("ZABBIX_API_URL is required", result.stderr)
        self.assertNotIn(sentinel, result.stderr)


class MutationApplyGateTests(unittest.TestCase):
    params = {"groups": [{"groupid": "2"}], "host": "edge-1"}
    digest = "79a1738c95fcc3be720fabc75b5bb0bf275250b6ccbef2a99b4e0bfd953487ec"

    def run_file_mutation(self, command, path, url, *gate_args, token="secret-token"):
        return run_cli(
            "hosts",
            command,
            "--params-file",
            str(path),
            *gate_args,
            env={
                **os.environ,
                "ZABBIX_API_URL": url,
                "ZABBIX_API_TOKEN": token,
            },
        )

    def test_apply_without_confirmation_fails_before_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps(self.params), encoding="utf-8")
            with fake_zabbix(lambda payload: rpc_result(payload, "5.4.12")) as (
                server,
                url,
            ):
                result = self.run_file_mutation("create", path, url, "--apply")

        self.assertEqual(result.returncode, 1)
        self.assertIn("confirm-digest", result.stderr)
        self.assertEqual(server.requests, [])

    def test_confirmation_without_apply_is_invalid_before_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps(self.params), encoding="utf-8")
            with fake_zabbix(lambda payload: rpc_result(payload, "5.4.12")) as (
                server,
                url,
            ):
                result = self.run_file_mutation(
                    "create", path, url, "--confirm-digest", self.digest
                )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--apply", result.stderr)
        self.assertEqual(server.requests, [])

    def test_malformed_digest_fails_before_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps(self.params), encoding="utf-8")
            with fake_zabbix(lambda payload: rpc_result(payload, "5.4.12")) as (
                server,
                url,
            ):
                result = self.run_file_mutation(
                    "create",
                    path,
                    url,
                    "--apply",
                    "--confirm-digest",
                    self.digest.upper(),
                )

        self.assertEqual(result.returncode, 1)
        self.assertIn("lowercase", result.stderr)
        self.assertEqual(server.requests, [])

    def test_unmatched_method_or_params_digest_fails_before_network_access(self):
        module = load_module()
        wrong_digests = {
            "different method": module.mutation_digest("host.update", self.params),
            "changed params": module.mutation_digest(
                "host.create", {**self.params, "host": "edge-2"}
            ),
        }
        for description, digest in wrong_digests.items():
            with self.subTest(description=description):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "payload.json"
                    path.write_text(json.dumps(self.params), encoding="utf-8")
                    with fake_zabbix(
                        lambda payload: rpc_result(payload, "5.4.12")
                    ) as (server, url):
                        result = self.run_file_mutation(
                            "create",
                            path,
                            url,
                            "--apply",
                            "--confirm-digest",
                            digest,
                        )
                self.assertEqual(result.returncode, 1)
                self.assertIn("does not match", result.stderr)
                self.assertEqual(server.requests, [])

    def test_matching_digest_probes_version_then_applies_only_approved_mutation(self):
        cases = {
            "create": self.params,
            "update": {"hostid": "10105", "name": "Edge One"},
        }
        module = load_module()
        for command, params in cases.items():
            with self.subTest(command=command):
                method = f"host.{command}"
                digest = module.mutation_digest(method, params)

                def responder(payload):
                    if payload["method"] == "apiinfo.version":
                        return rpc_result(payload, "5.4.12")
                    return rpc_result(payload, {"hostids": ["10105"]})

                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "payload.json"
                    path.write_text(json.dumps(params), encoding="utf-8")
                    with fake_zabbix(responder) as (server, url):
                        result = self.run_file_mutation(
                            command,
                            path,
                            url,
                            "--apply",
                            "--confirm-digest",
                            digest,
                        )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout), {"hostids": ["10105"]}
                )
                self.assertEqual(
                    [request["method"] for request in server.requests],
                    ["apiinfo.version", method],
                )
                self.assertNotIn("auth", server.requests[0])
                operation = server.requests[1]
                self.assertEqual(operation["auth"], "secret-token")
                self.assertEqual(operation["params"], params)
                self.assertNotIn("digest", operation)
                self.assertNotIn("sha256", operation)
                self.assertNotIn("confirm_digest", operation)

    def test_live_errors_never_expose_token_or_response_body(self):
        sentinel = "SENSITIVE-ZABBIX-TOKEN"
        error_responses = {
            "http 500": (500, {"detail": sentinel}),
            "malformed JSON": (200, f"not-json-{sentinel}".encode()),
            "JSON-RPC error": None,
        }
        for failing_stage in ("version", "mutation"):
            for description, static_response in error_responses.items():
                with self.subTest(stage=failing_stage, response=description):
                    def responder(payload):
                        is_failing_call = (
                            failing_stage == "version"
                            or payload["method"] != "apiinfo.version"
                        )
                        if not is_failing_call:
                            return rpc_result(payload, "5.4.12")
                        if static_response is not None:
                            return static_response
                        return 200, {
                            "jsonrpc": "2.0",
                            "error": {"code": -32602, "message": sentinel},
                            "id": payload["id"],
                        }

                    with tempfile.TemporaryDirectory() as directory:
                        path = Path(directory) / "payload.json"
                        path.write_text(json.dumps(self.params), encoding="utf-8")
                        with fake_zabbix(responder) as (_server, url):
                            result = self.run_file_mutation(
                                "create",
                                path,
                                url,
                                "--apply",
                                "--confirm-digest",
                                self.digest,
                                token=sentinel,
                            )

                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn(sentinel, result.stdout)
                    self.assertNotIn(sentinel, result.stderr)


class CurrentProblemTests(unittest.TestCase):
    def test_current_problems_probe_version_and_force_active_query(self):
        def responder(payload):
            if payload["method"] == "apiinfo.version":
                return rpc_result(payload, "5.4.12")
            return rpc_result(payload, [{"eventid": "42"}])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "params.json"
            path.write_text(
                '{"hostids": ["10105"], "recent": true}', encoding="utf-8"
            )
            with fake_zabbix(responder) as (server, url):
                result = run_cli(
                    "problems",
                    "current",
                    "--params-file",
                    str(path),
                    env={
                        **os.environ,
                        "ZABBIX_API_URL": url,
                        "ZABBIX_API_TOKEN": "secret-token",
                    },
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [{"eventid": "42"}])
        self.assertEqual(
            [request["method"] for request in server.requests],
            ["apiinfo.version", "problem.get"],
        )
        self.assertNotIn("auth", server.requests[0])
        operation = server.requests[1]
        self.assertEqual(operation["auth"], "secret-token")
        self.assertEqual(operation["params"]["output"], "extend")
        self.assertFalse(operation["params"]["recent"])
        self.assertEqual(operation["params"]["sortfield"], ["eventid"])
        self.assertEqual(operation["params"]["sortorder"], "DESC")
        self.assertEqual(operation["params"]["selectAcknowledges"], "extend")
        self.assertEqual(operation["params"]["selectTags"], "extend")
        self.assertEqual(operation["params"]["selectSuppressionData"], "extend")
        self.assertEqual(operation["params"]["hostids"], ["10105"])


class HistoricalProblemTests(unittest.TestCase):
    def test_history_uses_bounded_problem_events(self):
        module = load_module()
        params = module.historical_problem_params(
            "2026-01-01T00:00:00Z",
            "2026-01-31T23:59:59Z",
            {"hostids": ["10105"], "source": 3, "time_from": 1},
        )
        self.assertEqual(params["source"], 0)
        self.assertEqual(params["object"], 0)
        self.assertEqual(params["value"], 1)
        self.assertEqual(params["time_from"], 1767225600)
        self.assertEqual(params["time_till"], 1769903999)
        self.assertEqual(params["hostids"], ["10105"])
        self.assertEqual(params["sortfield"], ["clock", "eventid"])
        self.assertEqual(params["sortorder"], "DESC")

    def test_parse_timestamp_rejects_naive_value(self):
        module = load_module()
        with self.assertRaisesRegex(module.SkillError, "timezone"):
            module.parse_timestamp("2026-01-01T00:00:00")

    def test_parse_timestamp_normalizes_explicit_offset_to_utc(self):
        module = load_module()
        self.assertEqual(
            module.parse_timestamp("2026-01-01T02:00:00+02:00"),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def test_history_rejects_since_at_or_after_until(self):
        module = load_module()
        with self.assertRaisesRegex(module.SkillError, "before"):
            module.historical_problem_params(
                "2026-02-01T00:00:00Z", "2026-02-01T00:00:00Z", {}
            )

    def test_history_defaults_until_to_injected_aware_now(self):
        module = load_module()
        params = module.historical_problem_params(
            "2026-01-01T00:00:00Z",
            None,
            {},
            now=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(params["time_till"], 1769904000)

    def test_history_cli_probes_version_before_event_query(self):
        def responder(payload):
            if payload["method"] == "apiinfo.version":
                return rpc_result(payload, "5.4.12")
            return rpc_result(payload, [{"eventid": "41"}])

        with fake_zabbix(responder) as (server, url):
            result = run_cli(
                "problems",
                "history",
                "--since",
                "2026-01-01T00:00:00Z",
                "--until",
                "2026-01-31T23:59:59Z",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": "secret-token",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [{"eventid": "41"}])
        self.assertEqual(
            [request["method"] for request in server.requests],
            ["apiinfo.version", "event.get"],
        )
        self.assertNotIn("auth", server.requests[0])
        self.assertEqual(server.requests[1]["auth"], "secret-token")


class HostQueryTests(unittest.TestCase):
    @staticmethod
    def responder(payload):
        if payload["method"] == "apiinfo.version":
            return rpc_result(payload, "5.4.12")
        return rpc_result(payload, [{"hostid": "10105"}])

    def test_hosts_get_probes_version_and_uses_conservative_defaults(self):
        with fake_zabbix(self.responder) as (server, url):
            result = run_cli(
                "hosts",
                "get",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": "secret-token",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [{"hostid": "10105"}])
        self.assertEqual(
            [request["method"] for request in server.requests],
            ["apiinfo.version", "host.get"],
        )
        self.assertNotIn("auth", server.requests[0])
        self.assertEqual(server.requests[1]["auth"], "secret-token")
        self.assertEqual(
            server.requests[1]["params"],
            {
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
            },
        )

    def test_hosts_get_extra_params_override_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "params.json"
            path.write_text(
                json.dumps(
                    {
                        "filter": {"host": ["edge-1"]},
                        "output": ["hostid", "name"],
                    }
                ),
                encoding="utf-8",
            )
            with fake_zabbix(self.responder) as (server, url):
                result = run_cli(
                    "hosts",
                    "get",
                    "--params-file",
                    str(path),
                    env={
                        **os.environ,
                        "ZABBIX_API_URL": url,
                        "ZABBIX_API_TOKEN": "secret-token",
                    },
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        params = server.requests[1]["params"]
        self.assertEqual(params["filter"], {"host": ["edge-1"]})
        self.assertEqual(params["output"], ["hostid", "name"])


class ConfigurationTests(unittest.TestCase):
    def test_live_config_requires_full_http_url(self):
        zabbix_api = load_module()
        with self.assertRaisesRegex(zabbix_api.SkillError, "ZABBIX_API_URL"):
            zabbix_api.load_config(False, {})
        with self.assertRaisesRegex(zabbix_api.SkillError, "http or https"):
            zabbix_api.load_config(
                False, {"ZABBIX_API_URL": "ftp://zabbix/api_jsonrpc.php"}
            )
        with self.assertRaisesRegex(zabbix_api.SkillError, "ZABBIX_API_URL"):
            zabbix_api.load_config(
                False, {"ZABBIX_API_URL": "https://[invalid/api_jsonrpc.php"}
            )

    def test_config_rejects_nonnumeric_url_port(self):
        zabbix_api = load_module()
        with self.assertRaisesRegex(zabbix_api.SkillError, "ZABBIX_API_URL"):
            zabbix_api.load_config(
                False,
                {
                    "ZABBIX_API_URL": (
                        "http://127.0.0.1:not-a-port/api_jsonrpc.php"
                    )
                },
            )

    def test_config_rejects_whitespace_and_controls_in_url_components(self):
        zabbix_api = load_module()
        invalid_urls = {
            "hostname whitespace": "https://zabbix .example/api_jsonrpc.php",
            "hostname control": "https://zabbix\x01.example/api_jsonrpc.php",
            "path whitespace": "https://z.example/api jsonrpc.php",
            "path control": "https://z.example/api\njsonrpc.php",
            "query whitespace": "https://z.example/api_jsonrpc.php?name=bad value",
            "query control": "https://z.example/api_jsonrpc.php?name=bad\x7fvalue",
        }
        for description, url in invalid_urls.items():
            with self.subTest(description=description):
                with self.assertRaisesRegex(
                    zabbix_api.SkillError, "ZABBIX_API_URL"
                ):
                    zabbix_api.load_config(False, {"ZABBIX_API_URL": url})

    def test_config_rejects_malformed_percent_escapes_in_url_components(self):
        zabbix_api = load_module()
        invalid_urls = {
            "hostname": "https://zab%ZZ.example/api_jsonrpc.php",
            "path": "https://z.example/api%2_jsonrpc.php",
            "query": "https://z.example/api_jsonrpc.php?name=%GG",
        }
        for component, url in invalid_urls.items():
            with self.subTest(component=component):
                with self.assertRaisesRegex(
                    zabbix_api.SkillError, "ZABBIX_API_URL"
                ):
                    zabbix_api.load_config(False, {"ZABBIX_API_URL": url})

    def test_authenticated_config_requires_token_without_exposing_it(self):
        zabbix_api = load_module()
        with self.assertRaisesRegex(zabbix_api.SkillError, "ZABBIX_API_TOKEN"):
            zabbix_api.load_config(
                True, {"ZABBIX_API_URL": "https://z.example/api_jsonrpc.php"}
            )

    def test_config_rejects_credentials_embedded_in_url(self):
        zabbix_api = load_module()
        with self.assertRaisesRegex(
            zabbix_api.SkillError, "must not contain credentials"
        ):
            zabbix_api.load_config(
                False,
                {
                    "ZABBIX_API_URL": (
                        "https://user:pass@z.example/api_jsonrpc.php"
                    )
                },
            )

    def test_config_rejects_unreadable_ca_file_without_exposing_environment(self):
        zabbix_api = load_module()
        unrelated_value = "do-not-expose-this-value"
        with tempfile.TemporaryDirectory() as directory:
            missing_ca_file = str(Path(directory) / "missing.pem")
            with self.assertRaisesRegex(
                zabbix_api.SkillError, "ZABBIX_CA_FILE"
            ) as raised:
                zabbix_api.load_config(
                    False,
                    {
                        "ZABBIX_API_URL": "https://z.example/api_jsonrpc.php",
                        "ZABBIX_CA_FILE": missing_ca_file,
                        "UNRELATED_SECRET": unrelated_value,
                    },
                )
        self.assertNotIn(unrelated_value, str(raised.exception))

    def test_readable_invalid_ca_file_is_reported_without_traceback_or_secrets(self):
        secret = "SENSITIVE-CA-PATH-AND-CONTENTS"
        with tempfile.TemporaryDirectory() as directory:
            ca_file = Path(directory) / f"{secret}.pem"
            ca_file.write_text(secret, encoding="utf-8")
            result = run_cli(
                "version",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": "https://z.example/api_jsonrpc.php",
                    "ZABBIX_CA_FILE": str(ca_file),
                },
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("ZABBIX_CA_FILE", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn(secret, result.stderr)

    def test_config_preserves_readable_default_ca_file(self):
        ca_file = ssl.get_default_verify_paths().cafile
        if not ca_file or not Path(ca_file).is_file():
            self.skipTest("no readable default CA file is available")
        zabbix_api = load_module()
        config = zabbix_api.load_config(
            False,
            {
                "ZABBIX_API_URL": "https://z.example/api_jsonrpc.php",
                "ZABBIX_CA_FILE": ca_file,
            },
        )
        self.assertEqual(config.ca_file, ca_file)
        self.assertIsInstance(zabbix_api.build_ssl_context(config), ssl.SSLContext)


class TransportTests(unittest.TestCase):
    def test_version_command_sends_unauthenticated_json_rpc(self):
        with fake_zabbix(lambda payload: rpc_result(payload, "5.4.12")) as (
            server,
            url,
        ):
            result = run_cli("version", env={**os.environ, "ZABBIX_API_URL": url})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), "5.4.12")
        self.assertEqual(server.requests[0]["method"], "apiinfo.version")
        self.assertNotIn("auth", server.requests[0])

    def test_authenticated_call_places_token_only_in_auth_field(self):
        def responder(payload):
            return rpc_result(payload, [])

        with fake_zabbix(responder) as (server, url):
            module = load_module()
            client = module.ZabbixClient(
                module.ApiConfig(url, "secret-token", None)
            )
            self.assertEqual(client.call("host.get", {}, authenticated=True), [])
        self.assertEqual(server.requests[0]["auth"], "secret-token")
        self.assertNotIn("secret-token", json.dumps(server.requests[0]["params"]))

    def test_calls_use_monotonically_increasing_ids(self):
        with fake_zabbix(lambda payload: rpc_result(payload, [])) as (server, url):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, None, None))
            client.call("first.get", {}, authenticated=False)
            client.call("second.get", {}, authenticated=False)
        self.assertEqual([request["id"] for request in server.requests], [1, 2])

    def test_http_500_is_reported_concisely(self):
        with fake_zabbix(lambda payload: (500, {"detail": "internal"})) as (
            _server,
            url,
        ):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, None, None))
            with self.assertRaisesRegex(module.SkillError, "HTTP 500"):
                client.call("host.get", {}, authenticated=False)

    def test_malformed_json_is_reported_concisely(self):
        with fake_zabbix(lambda payload: (200, b"not-json")) as (_server, url):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, None, None))
            with self.assertRaisesRegex(module.SkillError, "malformed JSON"):
                client.call("host.get", {}, authenticated=False)

    def test_truncated_response_is_reported_without_body_or_token(self):
        token = "SENSITIVE-ZABBIX-TOKEN"
        partial_body = f'{{"secret":"{token}"'.encode()
        with fake_zabbix(
            lambda payload: (200, partial_body, len(partial_body) + 100)
        ) as (_server, url):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, token, None))
            with self.assertRaisesRegex(module.SkillError, "response") as raised:
                client.call("host.get", {}, authenticated=True)

        self.assertNotIn(token, str(raised.exception))
        self.assertNotIn(partial_body.decode(), str(raised.exception))

    def test_json_rpc_error_does_not_expose_response_or_token(self):
        token = "secret-token"

        def responder(payload):
            return 200, {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": token},
                "id": payload["id"],
            }

        with fake_zabbix(responder) as (_server, url):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, token, None))
            with self.assertRaisesRegex(module.SkillError, "JSON-RPC error") as raised:
                client.call("host.get", {}, authenticated=True)
        self.assertNotIn(token, str(raised.exception))

    def test_missing_result_is_rejected(self):
        def responder(payload):
            return 200, {"jsonrpc": "2.0", "id": payload["id"]}

        with fake_zabbix(responder) as (_server, url):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, None, None))
            with self.assertRaisesRegex(module.SkillError, "missing result"):
                client.call("host.get", {}, authenticated=False)

    def test_mismatched_response_id_is_rejected(self):
        def responder(payload):
            return 200, {"jsonrpc": "2.0", "result": [], "id": payload["id"] + 1}

        with fake_zabbix(responder) as (_server, url):
            module = load_module()
            client = module.ZabbixClient(module.ApiConfig(url, None, None))
            with self.assertRaisesRegex(module.SkillError, "response ID"):
                client.call("host.get", {}, authenticated=False)

    def test_timeout_is_reported_concisely(self):
        module = load_module()
        client = module.ZabbixClient(
            module.ApiConfig("https://z.example/api_jsonrpc.php", None, None)
        )
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(module.SkillError, "timed out"):
                client.call("host.get", {}, authenticated=False)

    def test_request_construction_failures_are_sanitized(self):
        module = load_module()
        secret = "SECRET-URL-CONTENTS"
        client = module.ZabbixClient(
            module.ApiConfig("https://z.example/api_jsonrpc.php", None, None)
        )
        failures = (
            ("urllib.request.Request", ValueError(secret)),
            ("urllib.request.urlopen", http.client.InvalidURL(secret)),
        )
        for target, failure in failures:
            with self.subTest(target=target):
                with mock.patch(target, side_effect=failure):
                    with self.assertRaisesRegex(
                        module.SkillError, "ZABBIX_API_URL"
                    ) as raised:
                        client.call("host.get", {}, authenticated=False)
                self.assertNotIn(secret, str(raised.exception))

    def test_request_serialization_rejects_non_json_numeric_constants(self):
        module = load_module()
        client = module.ZabbixClient(
            module.ApiConfig("https://z.example/api_jsonrpc.php", None, None)
        )
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with mock.patch("urllib.request.urlopen") as urlopen:
                    with self.assertRaisesRegex(module.SkillError, "JSON"):
                        client.call("host.get", {"value": value}, False)
                urlopen.assert_not_called()

    def test_response_rejects_non_json_numeric_constants(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                body = (
                    '{"jsonrpc":"2.0","result":'
                    + constant
                    + ',"id":1}'
                ).encode()
                with fake_zabbix(lambda payload, body=body: (200, body)) as (
                    _server,
                    url,
                ):
                    module = load_module()
                    client = module.ZabbixClient(module.ApiConfig(url, None, None))
                    with self.assertRaisesRegex(module.SkillError, "JSON"):
                        client.call("host.get", {}, authenticated=False)


class SuccessfulOutputSecrecyTests(unittest.TestCase):
    def test_successful_result_rejects_token_in_object_key_without_exposure(self):
        sentinel = "SENSITIVE-ZABBIX-TOKEN"
        secret_key = f"private-{sentinel}"

        def responder(payload):
            if payload["method"] == "apiinfo.version":
                return rpc_result(payload, "5.4.12")
            return rpc_result(
                payload,
                {
                    secret_key: "first",
                    "private-[REDACTED]": "second",
                },
            )

        with fake_zabbix(responder) as (_server, url):
            result = run_cli(
                "hosts",
                "get",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": sentinel,
                },
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("object key", result.stderr)
        self.assertNotIn(sentinel, result.stderr)
        self.assertNotIn(secret_key, result.stderr)

    def test_successful_result_recursively_redacts_configured_token_as_valid_json(self):
        sentinel = "SENSITIVE-ZABBIX-TOKEN"

        def responder(payload):
            if payload["method"] == "apiinfo.version":
                return rpc_result(payload, "5.4.12")
            return rpc_result(
                payload,
                {
                    "direct": sentinel,
                    "nested": [
                        {"message": f"before-{sentinel}-after"},
                        "safe",
                    ],
                },
            )

        with fake_zabbix(responder) as (_server, url):
            result = run_cli(
                "hosts",
                "get",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": sentinel,
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(sentinel, result.stdout)
        self.assertNotIn(sentinel, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "direct": "[REDACTED]",
                "nested": [
                    {"message": "before-[REDACTED]-after"},
                    "safe",
                ],
            },
        )


class VersionPolicyTests(unittest.TestCase):
    def test_version_policy_accepts_5_4_rejects_older_and_warns_newer(self):
        module = load_module()
        self.assertIsNone(module.check_supported_version("5.4.12"))
        with self.assertRaisesRegex(module.SkillError, "5.4 or newer"):
            module.check_supported_version("5.2.7")
        self.assertIn("not verified", module.check_supported_version("6.0.0"))

    def test_version_policy_rejects_malformed_versions(self):
        module = load_module()
        for version in (
            "",
            "5.4",
            "5.x.1",
            "5.4.12beta",
            "5.4.²",
            "5.-4.0",
        ):
            with self.subTest(version=version):
                with self.assertRaisesRegex(module.SkillError, "version"):
                    module.check_supported_version(version)

    def test_version_command_prints_warning_for_newer_versions(self):
        with fake_zabbix(lambda payload: rpc_result(payload, "6.0.0")) as (
            _server,
            url,
        ):
            result = run_cli("version", env={**os.environ, "ZABBIX_API_URL": url})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), "6.0.0")
        self.assertIn("not verified", result.stderr)


class CompatibilityWarningOrderingTests(unittest.TestCase):
    @staticmethod
    def responder(payload):
        if payload["method"] == "apiinfo.version":
            return rpc_result(payload, "6.0.0")
        return 200, {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "operation failed"},
            "id": payload["id"],
        }

    def assert_warning_precedes_operation_error(self, result):
        self.assertEqual(result.returncode, 1)
        lines = result.stderr.splitlines()
        self.assertEqual(sum("warning:" in line for line in lines), 1)
        self.assertGreaterEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("warning:"), lines)
        self.assertTrue(lines[-1].startswith("error:"), lines)

    def test_newer_version_warning_precedes_failed_authenticated_read(self):
        with fake_zabbix(self.responder) as (_server, url):
            result = run_cli(
                "hosts",
                "get",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": "secret-token",
                },
            )
        self.assert_warning_precedes_operation_error(result)

    def test_newer_version_warning_redacts_configured_token_before_failed_read(self):
        sentinel = "SENSITIVE-ZABBIX-TOKEN"

        def responder(payload):
            if payload["method"] == "apiinfo.version":
                return rpc_result(payload, f"6.0.0.{sentinel}")
            return 200, {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "operation failed"},
                "id": payload["id"],
            }

        with fake_zabbix(responder) as (server, url):
            result = run_cli(
                "hosts",
                "get",
                env={
                    **os.environ,
                    "ZABBIX_API_URL": url,
                    "ZABBIX_API_TOKEN": sentinel,
                },
            )

        self.assertEqual(
            [request["method"] for request in server.requests],
            ["apiinfo.version", "host.get"],
        )
        self.assertEqual(server.requests[1]["auth"], sentinel)
        self.assert_warning_precedes_operation_error(result)
        self.assertIn("Zabbix 6.0.0.[REDACTED]", result.stderr)
        self.assertIn("compatibility is not verified", result.stderr)
        self.assertNotIn(sentinel, result.stdout)
        self.assertNotIn(sentinel, result.stderr)

    def test_newer_version_warning_precedes_failed_authenticated_apply(self):
        params = {"host": "edge-1", "groups": [{"groupid": "2"}]}
        digest = load_module().mutation_digest("host.create", params)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "params.json"
            path.write_text(json.dumps(params), encoding="utf-8")
            with fake_zabbix(self.responder) as (_server, url):
                result = run_cli(
                    "hosts",
                    "create",
                    "--params-file",
                    str(path),
                    "--apply",
                    "--confirm-digest",
                    digest,
                    env={
                        **os.environ,
                        "ZABBIX_API_URL": url,
                        "ZABBIX_API_TOKEN": "secret-token",
                    },
                )
        self.assert_warning_precedes_operation_error(result)


if __name__ == "__main__":
    unittest.main()
