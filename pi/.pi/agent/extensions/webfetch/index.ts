import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { createWebFetchTool } from "./webfetch.ts";

export default function webfetchExtension(pi: ExtensionAPI) {
	pi.registerTool(createWebFetchTool());
}
