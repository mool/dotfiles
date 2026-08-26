import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import extension from "../index.ts";

const RPC_TIMEOUT_MS = 10_000;

type RpcResponse = Record<string, unknown>;
type CloseResult = { code: number | null; signal: NodeJS.Signals | null };
type RpcRunResult = CloseResult & {
	stdout: string;
	stderr: string;
	response?: RpcResponse;
};

async function withTimeout<T>(promise: Promise<T>, label: string): Promise<T> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	try {
		return await Promise.race([
			promise,
			new Promise<never>((_, reject) => {
				timer = setTimeout(() => reject(new Error(`${label} timed out`)), RPC_TIMEOUT_MS);
			}),
		]);
	} finally {
		if (timer !== undefined) {
			clearTimeout(timer);
		}
	}
}

async function runPiRpc(extensionPath: string): Promise<RpcRunResult> {
	const agentDir = await mkdtemp(join(tmpdir(), "pi-webfetch-rpc-"));
	const cliPath = fileURLToPath(
		new URL("../node_modules/@earendil-works/pi-coding-agent/dist/cli.js", import.meta.url),
	);
	const child = spawn(
		process.execPath,
		[
			cliPath,
			"--offline",
			"--mode",
			"rpc",
			"--no-session",
			"--no-builtin-tools",
			"--no-extensions",
			"--extension",
			extensionPath,
			"--tools",
			"webfetch",
			"--model",
			"openai-codex/gpt-5.5",
			"--no-context-files",
			"--no-skills",
			"--no-prompt-templates",
			"--no-themes",
		],
		{
			cwd: fileURLToPath(new URL("..", import.meta.url)),
			env: { ...process.env, PI_OFFLINE: "1", PI_CODING_AGENT_DIR: agentDir },
			stdio: ["pipe", "pipe", "pipe"],
		},
	);

	let stdout = "";
	let stderr = "";
	let outputBuffer = "";
	let responseObserved = false;
	let resolveResponse!: (response: RpcResponse) => void;
	const responsePromise = new Promise<RpcResponse>((resolve) => {
		resolveResponse = resolve;
	});
	let resolveClose!: (result: CloseResult) => void;
	let rejectClose!: (error: Error) => void;
	const closePromise = new Promise<CloseResult>((resolve, reject) => {
		resolveClose = resolve;
		rejectClose = reject;
	});

	child.stdout.setEncoding("utf8");
	child.stdout.on("data", (chunk: string) => {
		stdout += chunk;
		outputBuffer += chunk;
		let newlineIndex = outputBuffer.indexOf("\n");
		while (newlineIndex !== -1) {
			const line = outputBuffer.slice(0, newlineIndex).replace(/\r$/, "");
			outputBuffer = outputBuffer.slice(newlineIndex + 1);
			newlineIndex = outputBuffer.indexOf("\n");
			if (line.length === 0) {
				continue;
			}
			try {
				const parsed: unknown = JSON.parse(line);
				if (
					!responseObserved &&
					typeof parsed === "object" &&
					parsed !== null &&
					(parsed as RpcResponse).id === "webfetch-rpc-smoke" &&
					(parsed as RpcResponse).type === "response" &&
					(parsed as RpcResponse).command === "get_state"
				) {
					responseObserved = true;
					resolveResponse(parsed as RpcResponse);
				}
			} catch {
				// RPC stdout is JSONL; leave malformed output to the no-response assertion.
			}
		}
	});
	child.stderr.setEncoding("utf8");
	child.stderr.on("data", (chunk: string) => {
		stderr += chunk;
	});
	child.once("error", (error) => rejectClose(error));
	child.once("close", (code, signal) => resolveClose({ code, signal }));

	try {
		child.stdin.write(`${JSON.stringify({ id: "webfetch-rpc-smoke", type: "get_state" })}\n`);
		const outcome = await withTimeout(
			Promise.race([
				responsePromise.then((response) => ({ kind: "response" as const, response })),
				closePromise.then((close) => ({ kind: "close" as const, close })),
			]),
			"Pi RPC smoke",
		);
		let close: CloseResult;
		if (outcome.kind === "response") {
			child.stdin.end();
			close = await withTimeout(closePromise, "Pi RPC shutdown");
		} else {
			close = outcome.close;
		}
		return { ...close, stdout, stderr, response: outcome.kind === "response" ? outcome.response : undefined };
	} finally {
		if (child.exitCode === null && child.signalCode === null) {
			child.kill("SIGTERM");
		}
		try {
			await withTimeout(closePromise, "Pi RPC cleanup");
		} catch {
			if (child.exitCode === null && child.signalCode === null) {
				child.kill("SIGKILL");
			}
		}
		await rm(agentDir, { recursive: true, force: true });
	}
}

test("the extension registers exactly webfetch", () => {
	const registered: Array<{ name: string }> = [];
	const fakePi = {
		registerTool(tool: { name: string }) {
			registered.push(tool);
		},
	} as unknown as ExtensionAPI;

	extension(fakePi);

	assert.deepEqual(registered.map((tool) => tool.name), ["webfetch"]);
	assert.equal(registered.some((tool) => tool.name === "websearch"), false);
});

test("Pi CLI loads the explicit extension and answers RPC in offline mode", async () => {
	const extensionPath = fileURLToPath(new URL("../index.ts", import.meta.url));
	const result = await runPiRpc(extensionPath);

	assert.equal(result.code, 0, result.stderr);
	assert.equal(result.signal, null);
	assert.ok(result.response);
	assert.equal(result.response.type, "response");
	assert.equal(result.response.command, "get_state");
	assert.equal(result.response.success, true);
	assert.doesNotMatch(result.stderr, /Failed to load extension/);
});

test("Pi RPC rejects a missing extension instead of accepting get_state", async () => {
	const missingExtensionPath = fileURLToPath(new URL("../missing-extension.ts", import.meta.url));
	const result = await runPiRpc(missingExtensionPath);

	assert.notEqual(result.code, 0, result.stderr);
	assert.equal(result.signal, null);
	assert.equal(result.response, undefined);
	assert.match(result.stderr, /Failed to load extension/);
});
