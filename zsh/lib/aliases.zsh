alias ..='cd ..'
alias 2..='cd ../..'
alias 3..='cd ../../..'
alias 4..='cd ../../../..'
alias 5..='cd ../../../../..'

alias vim="$EDITOR"

if [[ "$EDITOR" == nvim ]]; then
  alias vimdiff='nvim -d'
fi

mkcd () {
  command mkdir -p -- "$1" && cd -- "$1"
}

mktmp () {
  cd "$(mktemp -d)"
}
