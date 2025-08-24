return {
	"qvalentin/helm-ls.nvim",
	ft = "helm",
	opts = {
		conceal_templates = {
			-- enable the replacement of templates with virtual text of their current values
			enabled = false, -- this might change to false in the future
		},
		indent_hints = {
			-- enable hints for indent and nindent functions
			enabled = true, -- tree-sitter must be setup for this feature
		},
	},
}
