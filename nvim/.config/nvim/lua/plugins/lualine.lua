return {
	"nvim-lualine/lualine.nvim", -- https://github.com/nvim-lualine/lualine.nvim
	dependencies = {
		"nvim-tree/nvim-web-devicons",
	},
	config = function()
		local lualine = require("lualine")
		-- get lualine theme
		local lualine_theme = require("lualine.themes.wombat")

		local function get_schema()
			local schema = require("yaml-companion").get_buf_schema(0)
			if schema.result[1].name == "none" then
				return ""
			end
			return schema.result[1].name
		end

		-- configure lualine with modified theme
		lualine.setup({
			options = {
				theme = lualine_theme,
			},
			sections = {
				lualine_x = { "fileformat", "filetype", get_schema },
			},
		})
	end,
}
