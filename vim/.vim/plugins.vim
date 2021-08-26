call plug#begin('~/.vim/plugged')

Plug 'airblade/vim-gitgutter'
Plug 'ap/vim-css-color'
Plug 'chrisbra/csv.vim'
Plug 'drewtempelmeyer/palenight.vim'
Plug 'elzr/vim-json'
Plug 'fatih/vim-go', { 'do': ':GoUpdateBinaries' }
Plug 'FooSoft/vim-argwrap'
Plug 'gagoar/SmartColumnColors'
Plug 'gagoar/StripWhiteSpaces'
Plug 'google/vim-jsonnet'
Plug 'hashivim/vim-packer'
Plug 'hashivim/vim-terraform'
Plug 'itchyny/lightline.vim'
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-easy-align'
Plug 'liuchengxu/vim-which-key'
Plug 'nathanaelkane/vim-indent-guides'
Plug 'neoclide/coc.nvim', {'branch': 'release'}
Plug 'neomake/neomake'
Plug 'pangloss/vim-javascript'
Plug 'rking/ag.vim'
Plug 'scrooloose/nerdcommenter'
Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'sudar/vim-arduino-syntax'
Plug 'sudar/vim-arduino-snippets'
Plug 'towolf/vim-helm'
Plug 'tpope/vim-endwise'
Plug 'tpope/vim-eunuch'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-markdown'
Plug 'tpope/vim-rails'
Plug 'tpope/vim-rake'
Plug 'tpope/vim-surround'
Plug 'vim-ruby/vim-ruby'
Plug 'Vimjas/vim-python-pep8-indent'

" plugins for vim-snipmate
Plug 'MarcWeber/vim-addon-mw-utils'
Plug 'tomtom/tlib_vim'
Plug 'garbas/vim-snipmate'
Plug 'honza/vim-snippets'

call plug#end()
