return {
	"nvim-tree/nvim-tree.lua",
	dependencies = { "nvim-tree/nvim-web-devicons" },
	config = function()
		local nvimtree = require("nvim-tree")

		-- recommended settings from nvim-tree documentation
		vim.g.loaded_netrw = 1
		vim.g.loaded_netrwPlugin = 1

		-- configure nvim-tree
		nvimtree.setup({
			-- disable window_picker for
			-- explorer to work well with
			-- window splits
			actions = {
				open_file = {
					window_picker = {
						enable = false,
					},
				},
			},
			-- 	git = {
			-- 		ignore = false,
			-- 	},
		})

		-- set keymaps
		local keymap = vim.keymap
		keymap.set("n", "<leader>e", ":NvimTreeToggle<CR>") -- toggle file explorer
	end,
}
