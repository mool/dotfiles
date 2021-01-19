alias k=kubectl
export PATH="${PATH}:${HOME}/.krew/bin"

INV_REPOS_PATH=$HOME/InVision
export INVISION_KUBECTL_CONFIG_PATH=$INV_REPOS_PATH/kubectl-config
source $INVISION_KUBECTL_CONFIG_PATH/kubectl.sh
