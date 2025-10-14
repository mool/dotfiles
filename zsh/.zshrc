#!/bin/zsh

# Configs
export DOTFILES=$HOME/.dotfiles
export EDITOR='nvim'
export AWS_PAGER=""

# Paths
export PATH="$HOME/bin:/usr/local/sbin:$PATH"

# export hombrew variables
if [ -f /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
else
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Zinit
ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
[ ! -d $ZINIT_HOME ] && mkdir -p "$(dirname $ZINIT_HOME)"
[ ! -d $ZINIT_HOME/.git ] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
source "${ZINIT_HOME}/zinit.zsh"

[ ! -d $ZSH_CACHE_DIR/completions ] && mkdir -p "$ZSH_CACHE_DIR/completions"

# Starship Prompt
zinit ice as"command" from"gh-r" \
          atclone"./starship init zsh > init.zsh; ./starship completions zsh > _starship" \
          atpull"%atclone" src"init.zsh"
zinit light starship/starship

# Zsh Plugins
zinit light zsh-users/zsh-syntax-highlighting
# zinit light zsh-users/zsh-completions

zinit snippet OMZ::lib/completion.zsh
zinit snippet OMZ::lib/directories.zsh
zinit snippet OMZ::lib/grep.zsh
zinit snippet OMZ::lib/history.zsh
zinit snippet OMZ::lib/key-bindings.zsh
zinit snippet OMZ::lib/theme-and-appearance.zsh

export SHOW_AWS_PROMPT=false
zinit snippet OMZP::aws
zinit snippet OMZP::docker
zinit snippet OMZP::docker-compose
zinit snippet OMZP::git
zinit snippet OMZP::helm
zinit snippet OMZP::terraform

autoload -Uz compinit
compinit

zinit cdreplay -q # execute compdefs provided by rest of plugins
# zi cdlist # look at gathered compdefs

# Source lib/*.zsh files
for config_file ($DOTFILES/zsh/lib/*.zsh); do
  source $config_file
done

export HISTORY_IGNORE="(access_token|accesstoken|AKIA|api_key|apikey|authonly|authorization|aws_access_key_id|aws_secret_access_key|bearer|client-secret|client_secret|current_key|eyjrijoi|gh_token|github_token|hooks.slack.com|id-token|id_token|kubectl --token=|kubectl config set-credentials|pagerduty_|password|private_key|private_key_id|read|refresh-token|refresh_token|refreshtoken|token|x-api-key|x-auth-key)"

if [[ -z $TMUX ]]; then
  if tmux list-sessions; then
    tmux attach-session
  else
    tmux new-session -s main
  fi
fi
