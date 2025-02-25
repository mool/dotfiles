return {
	"LudoPinelli/comment-box.nvim",
	config = function()
		require("comment-box").setup({
			borders = { -- symbols used to draw a box
				top = "#",
				bottom = "#",
				left = "#",
				right = "#",
				top_left = "#",
				top_right = "#",
				bottom_left = "#",
				bottom_right = "#",
			},
			lines = { -- symbols used to draw a line
				line = "#",
				line_start = "#",
				line_end = "#",
				title_left = "#",
				title_right = "#",
			},
			outer_blank_lines_above = false, -- insert a blank line above the box
			outer_blank_lines_below = false, -- insert a blank line below the box
			inner_blank_lines = false, -- insert a blank line above and below the text
			line_blank_line_above = false, -- insert a blank line above the line
			line_blank_line_below = false, -- insert a blank line below the line
		})
	end,
}
