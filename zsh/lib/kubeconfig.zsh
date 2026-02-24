source <(kubectl completion zsh)

export PATH="${PATH}:${HOME}/.krew/bin"

alias k=kubecolor
compdef kubecolor=kubectl
export KUBECOLOR_THEME_BASE_MUTED="white:italic"
