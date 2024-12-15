return {
	"nvim-treesitter/nvim-treesitter",
	event = { "BufReadPre", "BufNewFile" },
	build = ":TSUpdate",
	dependencies = {
		"windwp/nvim-ts-autotag",
	},
	config = function()
		-- import nvim-treesitter plugin
		local treesitter = require("nvim-treesitter.configs")

		-- configure treesitter
		treesitter.setup({ -- enable syntax highlighting
			highlight = {
				enable = true,
			},
			-- enable indentation
			indent = { enable = true },
			-- enable autotagging (w/ nvim-ts-autotag plugin)
			autotag = { enable = true },
			-- ensure these language parsers are installed
			ensure_installed = {
				"bash",
				"dockerfile",
				"gitignore",
				"gotmpl",
				"hcl",
				"helm",
				"html",
				"json",
				"lua",
				"markdown",
				"markdown_inline",
				"terraform",
				"vim",
				"yaml",
			},
			-- auto install above language parsers
			auto_install = true,
		})
	end,
}
