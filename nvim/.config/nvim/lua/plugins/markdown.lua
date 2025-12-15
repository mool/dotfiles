return {
	{
		"MeanderingProgrammer/render-markdown.nvim",
		dependencies = { "nvim-treesitter/nvim-treesitter", "nvim-mini/mini.nvim" }, -- if you use the mini.nvim suite
		-- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-mini/mini.icons' },        -- if you use standalone mini plugins
		-- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-tree/nvim-web-devicons' }, -- if you prefer nvim-web-devicons
		---@module 'render-markdown'
		---@type render.md.UserConfig
		opts = {},
	},
	{
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		ft = { "markdown" },
		build = function()
			vim.fn["mkdp#util#install"]()
		end,
	},
	-- {
	-- 	"preservim/vim-pencil",
	-- 	ft = "markdown",
	-- 	opt = false,
	-- 	config = function()
	-- 		vim.g["pencil#textwidth"] = 80
	-- 		vim.g["pencil#wrapModeDefault"] = "soft"
	--
	-- 		vim.api.nvim_create_autocmd("FileType", {
	-- 			pattern = "markdown", -- applied to markdown files
	-- 			callback = function()
	-- 				vim.opt_local.spell = true -- turn on spellcheck
	-- 				vim.cmd(":PencilSoft") -- enable hard wrapping
	-- 			end,
	-- 		})
	-- 	end,
	-- },
}
