import contextlib
import importlib.util
import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
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
        status, response = self.server.responder(payload)
        body = response if isinstance(response, bytes) else json.dumps(response).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
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


def run_cli(*args, env):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


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


if __name__ == "__main__":
    unittest.main()
