#!/bin/zsh

# Configs
export DOTFILES=$HOME/.dotfiles
export EDITOR='vim'
export AWS_PAGER=""

# Paths
export PATH="$HOME/bin:/usr/local/sbin:$PATH"

# export hombrew variables
if [ -f /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
else
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Set prompt config before loading the theme
source $DOTFILES/zsh/lib/spaceship-prompt.zsh

# Antigen
source $HOMEBREW_PREFIX/share/antigen/antigen.zsh
antigen init $DOTFILES/zsh/.antigenrc

# Source lib/*.zsh files
for config_file ($DOTFILES/zsh/lib/*.zsh); do
  source $config_file
done
