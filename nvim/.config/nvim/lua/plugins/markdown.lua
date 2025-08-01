return {
	{
		"tadmccorkle/markdown.nvim",
		ft = "markdown", -- or 'event = "VeryLazy"'
	},
	{
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		ft = { "markdown" },
		build = function()
			vim.fn["mkdp#util#install"]()
		end,
	},
	{
		"preservim/vim-pencil",
		ft = "markdown",
		opt = false,
		config = function()
			vim.g["pencil#textwidth"] = 80
			vim.g["pencil#wrapModeDefault"] = "hard"

			vim.api.nvim_create_autocmd("FileType", {
				pattern = "markdown", -- applied to markdown files
				callback = function()
					vim.opt_local.spell = true -- turn on spellcheck
					vim.cmd(":PencilHard") -- enable hard wrapping
				end,
			})
		end,
	},
}
