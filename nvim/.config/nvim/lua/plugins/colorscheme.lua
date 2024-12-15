return {
	"navarasu/onedark.nvim", -- https://github.com/navarasu/onedark.nvim
	lazy = false,
	priority = 1000,
	opts = {
		style = "warm",
	},
	init = function()
		require("onedark").load()
	end,
}
