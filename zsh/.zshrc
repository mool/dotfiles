#!/bin/zsh

autoload -Uz compinit
compinit -i

# Configs
export DOTFILES=$HOME/.dotfiles
export EDITOR='vim'
export AWS_PAGER=""

# Paths
export PATH="/usr/local/sbin:$PATH"

# Antibody
export ZSH="$(antibody home)/https-COLON--SLASH--SLASH-github.com-SLASH-ohmyzsh-SLASH-ohmyzsh"
source <(antibody init)
antibody bundle < ~/.zsh_plugins.txt

# Source lib/*.zsh files
for config_file ($DOTFILES/zsh/lib/*.zsh); do
  source $config_file
done

compinit -i
