source <(kubectl completion zsh)

export PATH="${PATH}:${HOME}/.krew/bin"
export KUBECONFIG=$HOME/.kube/config:$HOME/.kube/config.mool

alias k=kubectl
