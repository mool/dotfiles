alias cdw="cd ~/Chainlink/"

# Terragrunt

function update-tf-source() {
  file=${1:?missing file}
  sha=${2?missing sha}
  comment=${3:-$(date +%F)}
  gsed -i "s/\?ref=.*/?ref=$sha\" # $comment/" $file
}

# Kubernetes functions

function cordon-node() {
    cluster=${1:?missing cluster}
    node=${2:?missing node}

    kubectl --context $cluster cordon $node
}

function drain-node() {
    cluster=${1:?missing cluster}
    node=${2:?missing node}

    kubectl --context $cluster drain --force --ignore-daemonsets --delete-emptydir-data --timeout=180s $node
}

function bounce-node() {
    profile=${1:?missing profile}
    cluster=${2:?missing cluster}
    node=${3:?missing node}

    drain-node $cluster $node
    terminate-instance $profile $(node2id $profile $node)
}
