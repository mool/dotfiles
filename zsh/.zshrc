#!/bin/zsh

# Configs
export DOTFILES=$HOME/.dotfiles
export EDITOR='vim'

# Paths
export PATH="/usr/local/sbin:$PATH"

# Antibody
export ZSH="$(antibody home)/https-COLON--SLASH--SLASH-github.com-SLASH-robbyrussell-SLASH-oh-my-zsh"
source <(antibody init)
antibody bundle < ~/.zsh_plugins.txt

# Source lib/*.zsh files
for config_file ($DOTFILES/zsh/lib/*.zsh); do
  source $config_file
done
