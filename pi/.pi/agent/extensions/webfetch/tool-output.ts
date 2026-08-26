import {
	DEFAULT_MAX_BYTES,
	DEFAULT_MAX_LINES,
	formatSize,
	truncateHead,
	type TruncationResult,
} from "@earendil-works/pi-coding-agent";
import type { FetchPageResult } from "./fetch-page.ts";
import { err, ok, type Result } from "./result.ts";
import { writeTempTextFile } from "./temp.ts";
import { renderTruncatedTextOutput } from "./truncation.ts";
import type { WebFetchFormat } from "./types.ts";

export interface ToolOutputStore {
	writeTextFile(prefix: string, fileName: string, content: string): Promise<Result<string, ToolOutputStoreError>>;
}

export type ToolOutputStoreError = { readonly _tag: "TempFileWriteFailed"; readonly cause: unknown };

export class TempFileToolOutputStore implements ToolOutputStore {
	/** Write full tool output to a temporary text file. */
	async writeTextFile(prefix: string, fileName: string, content: string): Promise<Result<string, ToolOutputStoreError>> {
		try {
			return ok(await writeTempTextFile(prefix, fileName, content));
		} catch (cause: unknown) {
			return err({ _tag: "TempFileWriteFailed", cause });
		}
	}
}

export type PiTextContent = { readonly type: "text"; readonly text: string };
export type PiImageContent = { readonly type: "image"; readonly data: string; readonly mimeType: string };

export interface PiToolResult<Details> {
	readonly content: Array<PiTextContent | PiImageContent>;
	readonly details: Details;
}

export interface WebFetchDetails {
	readonly requestedUrl: string;
	readonly finalUrl: string;
	readonly format: WebFetchFormat;
	readonly status: number;
	readonly mime: string;
	readonly contentType: string;
	readonly charset?: string;
	readonly decoder?: string;
	readonly bytes: number;
	readonly image?: boolean;
	readonly truncated?: boolean;
	readonly fullOutputPath?: string;
}

interface ProjectedTextOutput {
	readonly text: string;
	readonly truncated: boolean;
	readonly fullOutputPath?: string;
	readonly truncation: TruncationResult;
}

/** Project a fetch-page service result to a Pi tool result with truncation protection. */
export async function projectFetchPageResultToPiToolResult(
	result: FetchPageResult,
	store: ToolOutputStore,
): Promise<Result<PiToolResult<WebFetchDetails>, ToolOutputStoreError>> {
	if (result._tag === "Image") {
		return ok({
			content: [
				textContent(`Fetched image from ${result.finalUrl} (${result.mime || "image"}, ${formatSize(result.bytes)})`),
				imageContent(result.data.toString("base64"), result.mime),
			],
			details: {
				requestedUrl: result.requestedUrl,
				finalUrl: result.finalUrl,
				format: result.format,
				status: result.status,
				mime: result.mime,
				contentType: result.contentType,
				bytes: result.bytes,
				image: true,
			},
		});
	}

	const truncated = await projectTextOutput(result.text, {
		store,
		tempPrefix: "pi-webfetch-",
		fileName: "output.txt",
	});
	if (truncated._tag === "err") {
		return truncated;
	}

	return ok({
		content: [textContent(truncated.value.text)],
		details: {
			requestedUrl: result.requestedUrl,
			finalUrl: result.finalUrl,
			format: result.format,
			status: result.status,
			mime: result.mime,
			contentType: result.contentType,
			charset: result.charset,
			decoder: result.decoder,
			bytes: result.bytes,
			truncated: truncated.value.truncated,
			fullOutputPath: truncated.value.fullOutputPath,
		},
	});
}

async function projectTextOutput(
	output: string,
	options: { readonly store: ToolOutputStore; readonly tempPrefix: string; readonly fileName: string },
): Promise<Result<ProjectedTextOutput, ToolOutputStoreError>> {
	const truncation = truncateHead(output, {
		maxBytes: DEFAULT_MAX_BYTES,
		maxLines: DEFAULT_MAX_LINES,
	});

	if (!truncation.truncated) {
		return ok({ text: truncation.content, truncated: false, truncation });
	}

	const fullOutputPath = await options.store.writeTextFile(options.tempPrefix, options.fileName, output);
	if (fullOutputPath._tag === "err") {
		return fullOutputPath;
	}

	const rendered = renderTruncatedTextOutput(output, {
		maxBytes: DEFAULT_MAX_BYTES,
		maxLines: DEFAULT_MAX_LINES,
		fullOutputPath: fullOutputPath.value,
	});
	return ok({
		text: rendered.text,
		truncated: rendered.truncated,
		fullOutputPath: rendered.fullOutputPath,
		truncation: rendered.truncation,
	});
}

function textContent(text: string): PiTextContent {
	return { type: "text", text };
}

function imageContent(data: string, mimeType: string): PiImageContent {
	return { type: "image", data, mimeType };
}
