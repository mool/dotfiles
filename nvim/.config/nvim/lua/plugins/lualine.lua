return {
  'nvim-lualine/lualine.nvim', -- https://github.com/nvim-lualine/lualine.nvim
  dependencies = {
    'nvim-tree/nvim-web-devicons',
  },
  config = function()
    local lualine = require('lualine')
    -- get lualine theme
    local lualine_theme = require("lualine.themes.wombat")

    -- configure lualine with modified theme
    lualine.setup({
      options = {
        theme = lualine_theme,
      },
    })
  end,
}
