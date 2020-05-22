alias k=kubectl

export KUBECONFIG=$HOME/.kube/config

INV_REPOS_PATH=$HOME/InVision
INVISION_KUBECONFIG_PATH=$INV_REPOS_PATH/cluster-provisioning/kubeconfig
PLATFORM_ONE_PATH=$INV_REPOS_PATH/platform-one-infra
CLUSTERS=(
  ops-221185518522
  ops-test-556453037222
)

for f in $(ls $INVISION_KUBECONFIG_PATH); do
  export KUBECONFIG=$KUBECONFIG:$INVISION_KUBECONFIG_PATH/$f
done

for cluster in "${CLUSTERS[@]}"; do
  export KUBECONFIG=$KUBECONFIG:$PLATFORM_ONE_PATH/$cluster/kubeconfig
done
