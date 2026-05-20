import { StringEnum, Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search";

const BraveSearchParams = Type.Object({
	query: Type.String({ description: "Search query to send to Brave Search." }),
	count: Type.Optional(
		Type.Number({
			description: "Number of results to return. Defaults to 5; maximum 10.",
			minimum: 1,
			maximum: 10,
		}),
	),
	offset: Type.Optional(
		Type.Number({
			description: "Result offset for pagination. Defaults to 0.",
			minimum: 0,
		}),
	),
	country: Type.Optional(
		Type.String({
			description: "Country code for localized results, or 'all' for global results. Defaults to 'all'.",
		}),
	),
	search_lang: Type.Optional(
		Type.String({
			description: "Search language code. Defaults to 'en'.",
		}),
	),
	safesearch: Type.Optional(
		StringEnum(["off", "moderate", "strict"] as const, {
			description: "Safe search setting. Defaults to 'moderate'.",
		}),
	),
});

type BraveSearchResult = {
	title?: string;
	url?: string;
	description?: string;
	age?: string;
	profile?: { name?: string };
};

type BraveSearchResponse = {
	web?: {
		results?: BraveSearchResult[];
	};
};

function clampInteger(value: unknown, fallback: number, min: number, max: number): number {
	if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
	return Math.max(min, Math.min(max, Math.trunc(value)));
}

function formatResults(results: BraveSearchResult[]): string {
	if (results.length === 0) return "No web results found.";

	return results
		.map((result, index) => {
			const title = result.title?.trim() || "Untitled result";
			const url = result.url?.trim() || "No URL";
			const description = result.description?.trim();
			const age = result.age?.trim();
			const source = result.profile?.name?.trim();

			const lines = [`${index + 1}. ${title}`, `   ${url}`];
			if (description) lines.push(`   ${description}`);
			if (source || age) {
				const metadata = [source, age].filter(Boolean).join(" · ");
				lines.push(`   ${metadata}`);
			}
			return lines.join("\n");
		})
		.join("\n\n");
}

const braveSearchTool = defineTool({
	name: "web_search",
	label: "Web Search",
	description:
		"Search the web using the Brave Search API. Returns compact web results with titles, URLs, and snippets.",
	promptSnippet: "Search the web using the Brave Search API for up-to-date information.",
	promptGuidelines: [
		"Use web_search when the user asks for current, recent, or external web information that is not available in local files.",
		"Prefer web_search over guessing when facts may have changed after the model's knowledge cutoff.",
	],
	parameters: BraveSearchParams,
	prepareArguments(args) {
		if (!args || typeof args !== "object") return args;
		const input = args as Record<string, unknown>;
		return {
			...input,
			count: typeof input.count === "string" ? Number(input.count) : input.count,
			offset: typeof input.offset === "string" ? Number(input.offset) : input.offset,
		};
	},

	async execute(_toolCallId, params, signal) {
		const apiKey = process.env.BRAVE_SEARCH_API_KEY;
		if (!apiKey) {
			throw new Error("BRAVE_SEARCH_API_KEY is not set. Export it before using web_search.");
		}

		const query = params.query.trim();
		if (!query) throw new Error("Search query cannot be empty.");

		const count = clampInteger(params.count, 5, 1, 10);
		const offset = clampInteger(params.offset, 0, 0, 20);
		const country = (params.country?.trim() || "all").toLowerCase();
		const searchLang = params.search_lang?.trim() || "en";
		const safesearch = params.safesearch || "moderate";

		const url = new URL(BRAVE_SEARCH_ENDPOINT);
		url.search = new URLSearchParams({
			q: query,
			count: String(count),
			offset: String(offset),
			country,
			search_lang: searchLang,
			safesearch,
		}).toString();

		const response = await fetch(url, {
			headers: {
				Accept: "application/json",
				"X-Subscription-Token": apiKey,
			},
			signal,
		});

		const responseText = await response.text();
		let body: BraveSearchResponse | undefined;
		try {
			body = responseText ? (JSON.parse(responseText) as BraveSearchResponse) : undefined;
		} catch {
			body = undefined;
		}

		if (!response.ok) {
			const message = responseText.slice(0, 500) || response.statusText;
			throw new Error(`Brave Search API error ${response.status}: ${message}`);
		}

		const results = body?.web?.results?.slice(0, count) ?? [];
		return {
			content: [{ type: "text", text: formatResults(results) }],
			details: {
				query,
				count,
				offset,
				country,
				search_lang: searchLang,
				safesearch,
				resultCount: results.length,
				results,
			},
		};
	},
});

export default function (pi: ExtensionAPI) {
	pi.registerTool(braveSearchTool);
}
