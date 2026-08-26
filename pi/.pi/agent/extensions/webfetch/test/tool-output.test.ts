import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { ok, type Result } from "../result.ts";
import {
  projectFetchPageResultToPiToolResult,
  type ToolOutputStore,
  type ToolOutputStoreError,
} from "../tool-output.ts";
import { parsePublicHttpUrl } from "../types.ts";

class RecordingStore implements ToolOutputStore {
  constructor(private readonly outputPath: string) {}

  async writeTextFile(
    _prefix: string,
    _fileName: string,
    content: string,
  ): Promise<Result<string, ToolOutputStoreError>> {
    await import("node:fs/promises").then(({ writeFile }) => writeFile(this.outputPath, content, "utf8"));
    return ok(this.outputPath);
  }
}

test("fetch text projection preserves details and saves oversized output", async () => {
  const parsed = parsePublicHttpUrl("https://example.com/page");
  assert.equal(parsed._tag, "ok");
  if (parsed._tag !== "ok") return;

  const outputPath = "/tmp/pi-webfetch-projection-test.txt";
  const result = await projectFetchPageResultToPiToolResult(
    {
      _tag: "Text",
      requestedUrl: parsed.value,
      finalUrl: parsed.value,
      format: "markdown",
      status: 200,
      mime: "text/plain",
      contentType: "text/plain",
      decoder: "utf-8",
      bytes: 100,
      text: Array.from({ length: 2101 }, (_, index) => `line ${index + 1}`).join("\n"),
    },
    new RecordingStore(outputPath),
  );

  assert.equal(result._tag, "ok");
  if (result._tag !== "ok") return;
  assert.equal(result.value.details.truncated, true);
  assert.equal(result.value.details.fullOutputPath, outputPath);
  assert.match(result.value.content[0]?.type === "text" ? result.value.content[0].text : "", /Output truncated/);
  assert.match(await readFile(outputPath, "utf8"), /line 2101/);
});

test("fetch text projection enforces the 50 KiB byte cap below the line cap", async () => {
  const parsed = parsePublicHttpUrl("https://example.com/large-page");
  assert.equal(parsed._tag, "ok");
  if (parsed._tag !== "ok") return;

  const output = Array.from({ length: 1000 }, (_, index) => `line ${index + 1} ${"x".repeat(100)}`).join("\n");
  assert.equal(output.split("\n").length, 1000);
  assert.ok(Buffer.byteLength(output, "utf8") > 50 * 1024);

  const outputPath = "/tmp/pi-webfetch-byte-cap-test.txt";
  const result = await projectFetchPageResultToPiToolResult(
    {
      _tag: "Text",
      requestedUrl: parsed.value,
      finalUrl: parsed.value,
      format: "markdown",
      status: 200,
      mime: "text/plain",
      contentType: "text/plain",
      decoder: "utf-8",
      bytes: Buffer.byteLength(output, "utf8"),
      text: output,
    },
    new RecordingStore(outputPath),
  );

  assert.equal(result._tag, "ok");
  if (result._tag !== "ok") return;
  assert.equal(result.value.details.truncated, true);
  assert.equal(result.value.details.fullOutputPath, outputPath);
  const projectedText = result.value.content[0]?.type === "text" ? result.value.content[0].text : "";
  assert.match(projectedText, /Output truncated/);
  assert.ok(Buffer.byteLength(projectedText, "utf8") <= 50 * 1024);
  assert.ok(projectedText.split("\n").length <= 2_000);
  assert.equal(await readFile(outputPath, "utf8"), output);
});

test("fetch image projection returns inline Pi image content", async () => {
  const parsed = parsePublicHttpUrl("https://example.com/image.png");
  assert.equal(parsed._tag, "ok");
  if (parsed._tag !== "ok") return;

  const result = await projectFetchPageResultToPiToolResult(
    {
      _tag: "Image",
      requestedUrl: parsed.value,
      finalUrl: parsed.value,
      format: "markdown",
      status: 200,
      mime: "image/png",
      contentType: "image/png",
      bytes: 3,
      data: Buffer.from([1, 2, 3]),
    },
    new RecordingStore("/tmp/pi-webfetch-image-test.txt"),
  );

  assert.equal(result._tag, "ok");
  if (result._tag !== "ok") return;
  assert.equal(result.value.details.image, true);
  assert.deepEqual(result.value.content[1], {
    type: "image",
    data: "AQID",
    mimeType: "image/png",
  });
});
