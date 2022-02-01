#!/bin/zsh

# Configs
export DOTFILES=$HOME/.dotfiles
export EDITOR='vim'
export AWS_PAGER=""

# Paths
export PATH="$HOME/bin:/usr/local/sbin:$PATH"

# Set prompt config before loading the theme
source $DOTFILES/zsh/lib/spaceship-prompt.zsh

# Antigen
source /usr/local/share/antigen/antigen.zsh
antigen init $DOTFILES/zsh/.antigenrc

# Source lib/*.zsh files
for config_file ($DOTFILES/zsh/lib/*.zsh); do
  source $config_file
done
