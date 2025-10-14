source <(kubectl completion zsh)

export PATH="${PATH}:${HOME}/.krew/bin"
export KUBECONFIG=$HOME/.kube/config:$HOME/.kube/config.mool

alias k=kubecolor
compdef kubecolor=kubectl
export KUBECOLOR_THEME_BASE_MUTED="white:italic"
