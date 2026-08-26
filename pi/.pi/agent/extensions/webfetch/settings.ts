import {
	type WebFetchFormat,
	type WebToolsSettings,
} from "./types.ts";

export const WEB_FETCH_FORMATS = ["markdown", "text", "html"] as const satisfies readonly WebFetchFormat[];

export const FETCH_TIMEOUT_SECONDS = {
	default: 30,
	min: 1,
	max: 120,
} as const;

export const FETCH_MAX_RESPONSE_BYTES = 5 * 1024 * 1024;
export const FETCH_MAX_REDIRECTS = 5;

export type ToolInputParseError =
	| { readonly _tag: "InvalidToolInput"; readonly message: string }
	| { readonly _tag: "InvalidToolField"; readonly field: string; readonly message: string }
	| { readonly _tag: "UnknownToolField"; readonly field: string };

const DEFAULTS = {
	fetchDefaultFormat: "markdown",
	fetchTimeoutSeconds: FETCH_TIMEOUT_SECONDS.default,
	fetchMaxResponseBytes: FETCH_MAX_RESPONSE_BYTES,
	fetchBlockPrivateHosts: true,
	fetchMaxRedirects: FETCH_MAX_REDIRECTS,
	fetchFallbackUserAgent: "opencode",
} as const;

/** Clamp a finite number to an inclusive integer range. */
export function clampInteger(
	value: number,
	bounds: { readonly min: number; readonly max: number; readonly fallback: number },
): number {
	if (!Number.isFinite(value)) {
		return bounds.fallback;
	}

	return Math.max(bounds.min, Math.min(bounds.max, Math.round(value)));
}

/** Return the fetch settings used by the webfetch tool. */
export function getWebFetchSettings(): WebToolsSettings["fetch"] {
	return {
		defaultFormat: DEFAULTS.fetchDefaultFormat,
		timeoutSeconds: DEFAULTS.fetchTimeoutSeconds,
		maxResponseBytes: DEFAULTS.fetchMaxResponseBytes,
		blockPrivateHosts: DEFAULTS.fetchBlockPrivateHosts,
		maxRedirects: DEFAULTS.fetchMaxRedirects,
		fallbackUserAgent: DEFAULTS.fetchFallbackUserAgent,
	};
}
