return {
	"williamboman/mason.nvim",
	dependencies = {
		"williamboman/mason-lspconfig.nvim",
		"WhoIsSethDaniel/mason-tool-installer.nvim",
	},
	config = function()
		-- import mason
		local mason = require("mason")

		-- import mason-lspconfig
		local mason_lspconfig = require("mason-lspconfig")

		local mason_tool_installer = require("mason-tool-installer")

		-- enable mason and configure icons
		mason.setup({
			ui = {
				icons = {
					package_installed = "✓",
					package_pending = "➜",
					package_uninstalled = "✗",
				},
			},
		})

		mason_lspconfig.setup({
			-- list of servers for mason to install
			ensure_installed = {
				"bashls",
				"docker_compose_language_service",
				"golangci_lint_ls",
				"gopls",
				"helm_ls",
				"lua_ls",
				"marksman",
				"pylsp",
				"terraformls",
				"tflint",
				"yamlls",
			},
			-- auto-install configured servers (with lspconfig)
			automatic_installation = false, -- not the same as ensure_installed
			automatic_enable = false,
		})

		mason_tool_installer.setup({
			ensure_installed = {
				"prettier", -- prettier formatter
				"stylua", -- lua formatter
				"isort", -- python formatter
				"black", -- python formatter
				"pylint", -- python linter
				"beautysh",
				"jq",
				"markdownlint-cli2",
				"markdown-toc",
				"golangci-lint",
				-- "gofmt",
				-- "goimports",
				-- "hclfmt",
				-- "terraform_fmt",
			},
		})
	end,
}
