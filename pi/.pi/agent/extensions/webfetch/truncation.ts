import {
	DEFAULT_MAX_BYTES,
	DEFAULT_MAX_LINES,
	formatSize,
	type TruncationResult,
	truncateHead,
} from "@earendil-works/pi-coding-agent";
import { writeTempTextFile } from "./temp.ts";

export interface TruncatedTextOutput {
	text: string;
	truncated: boolean;
	fullOutputPath?: string;
	truncation: TruncationResult;
}

export async function truncateTextOutput(
	output: string,
	options: {
		maxBytes?: number;
		maxLines?: number;
		tempPrefix: string;
		fileName?: string;
	},
): Promise<TruncatedTextOutput> {
	const maxBytes = options.maxBytes ?? DEFAULT_MAX_BYTES;
	const maxLines = options.maxLines ?? DEFAULT_MAX_LINES;
	const truncation = truncateHead(output, { maxBytes, maxLines });

	if (!truncation.truncated) {
		return {
			text: truncation.content,
			truncated: false,
			truncation,
		};
	}

	const fullOutputPath = await writeTempTextFile(options.tempPrefix, options.fileName ?? "output.txt", output);
	return renderTruncatedTextOutput(output, { maxBytes, maxLines, fullOutputPath });
}

/** Render a bounded preview and truncation notice after the full output has been saved. */
export function renderTruncatedTextOutput(
	output: string,
	options: {
		readonly maxBytes?: number;
		readonly maxLines?: number;
		readonly fullOutputPath: string;
	},
): TruncatedTextOutput {
	const maxBytes = options.maxBytes ?? DEFAULT_MAX_BYTES;
	const maxLines = options.maxLines ?? DEFAULT_MAX_LINES;
	let truncation = truncateHead(output, { maxBytes, maxLines });

	if (!truncation.truncated) {
		return {
			text: truncation.content,
			truncated: false,
			truncation,
		};
	}

	const previewMaxLines = Math.max(0, maxLines - 2);
	for (let attempt = 0; attempt < 5; attempt += 1) {
		const notice = createTruncationNotice(truncation, options.fullOutputPath);
		const noticePrefix = `\n\n${notice}`;
		const previewMaxBytes = Math.max(0, maxBytes - Buffer.byteLength(noticePrefix, "utf8"));
		truncation = truncateHead(output, {
			maxBytes: previewMaxBytes,
			maxLines: previewMaxLines,
		});
		const text = truncation.content + `\n\n${createTruncationNotice(truncation, options.fullOutputPath)}`;
		if (Buffer.byteLength(text, "utf8") <= maxBytes && text.split("\n").length <= maxLines) {
			return {
				text,
				truncated: true,
				fullOutputPath: options.fullOutputPath,
				truncation,
			};
		}
	}

	const text = truncation.content + `\n\n${createTruncationNotice(truncation, options.fullOutputPath)}`;
	return {
		text,
		truncated: true,
		fullOutputPath: options.fullOutputPath,
		truncation,
	};
}

function createTruncationNotice(
	truncation: TruncationResult,
	fullOutputPath: string,
): string {
	const omittedLines = truncation.totalLines - truncation.outputLines;
	const omittedBytes = truncation.totalBytes - truncation.outputBytes;
	let notice = `[Output truncated: showing ${truncation.outputLines} of ${truncation.totalLines} lines`;
	notice += ` (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)}).`;
	notice += ` ${omittedLines} lines (${formatSize(omittedBytes)}) omitted.`;
	notice += ` Full output saved to: ${fullOutputPath}]`;
	return notice;
}
