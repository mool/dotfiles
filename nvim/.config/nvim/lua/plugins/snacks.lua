return {
	"folke/snacks.nvim",
	dependencies = {
		"echasnovski/mini.icons",
	},
	priority = 1000,
	lazy = false,
	opts = {
		bigfile = { enabled = false },
		dashboard = {
			enabled = true,
			preset = {
				header = [[
                                              
       ████ ██████           █████      ██
      ███████████             █████ 
      █████████ ███████████████████ ███   ███████████
     █████████  ███    █████████████ █████ ██████████████
    █████████ ██████████ █████████ █████ █████ ████ █████
  ███████████ ███    ███ █████████ █████ █████ ████ █████
 ██████  █████████████████████ ████ █████ █████ ████ ██████
        ]],
			},
		},
		indent = { enabled = false },
		input = { enabled = false },
		git = { enabled = false },
		picker = { enabled = false },
		notifier = { enabled = false },
		quickfile = { enabled = false },
		scroll = { enabled = false },
		statuscolumn = { enabled = false },
		words = { enabled = false },
	},
	-- keys = {
	--   { "<leader>sf",       function() Snacks.scratch() end,            desc = "Toggle Scratch Buffer" },
	--   { "<leader>S",        function() Snacks.scratch.select() end,     desc = "Select Scratch Buffer" },
	--   { "<leader>gl",       function() Snacks.lazygit.log_file() end,   desc = "Lazygit Log (cwd)" },
	--   { "<leader>lg",       function() Snacks.lazygit() end,            desc = "Lazygit" },
	--   { "<C-p>",            function() Snacks.picker.pick("files") end, desc = "Find Files" },
	--   { "<leader><leader>", function() Snacks.picker.recent() end,      desc = "Recent Files" },
	--   { "<leader>fb",       function() Snacks.picker.buffers() end,     desc = "Buffers" },
	--   { "<leader>fg",       function() Snacks.picker.grep() end,        desc = "Grep Files" },
	--   { "<C-n>",            function() Snacks.explorer() end,           desc = "Explorer" },
	-- }
}
