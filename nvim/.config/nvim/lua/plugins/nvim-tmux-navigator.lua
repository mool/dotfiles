return {
	"christoomey/vim-tmux-navigator",
	dependencies = {
		"paulbkim-dev/vim-herdr-navigation",
	},
	lazy = false,
	init = function()
		vim.g.tmux_navigator_no_mappings = 1
	end,
	config = function()
		dofile(vim.fn.stdpath("data") .. "/lazy/vim-herdr-navigation/editor/nvim.lua")
	end,
}
