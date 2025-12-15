function aws-sso-login() {
  sessions=$(grep sso-session ~/.aws/config | awk '{print $2}' | sed 's/]//')

  if [[ $(echo $sessions | wc -w) -gt 1 ]]; then
    session=$(echo "$sessions" | fzf)
  else
    session=$sessions
  fi

  # session=$(grep sso-session ~/.aws/config | awk '{print $2}' | sed 's/]//' | fzf)
  aws sso login --sso-session "$session"
}

function node2id() {
    profile=${1:?missing profile}
    node=${2:?missing node}

    if echo $node | grep -q "internal"; then
        id=$(aws ec2 describe-instances --region us-west-2 --filters Name="network-interface.private-dns-name",Values="$node" --profile $profile | jq -r '.Reservations[].Instances[].InstanceId')
    else
        id=$(aws ec2 describe-instances --region us-west-2 --filters Name="network-interface.private-ip-address",Values="$node" --profile $profile | jq -r '.Reservations[].Instances[].InstanceId')
    fi
    echo $id
}

function terminate-instance() {
    profile=${1:?missing profile}
    instance_id=${2:?missing instance_id}

    aws ec2 terminate-instances --instance-ids $instance_id --profile $profile --region us-west-2
}

function terminate-node() {
    profile=${1:?missing profile}
    node=${2:?missing node}

    terminate-instance $profile $(node2id $profile $node)
}

function ssm-session() {
    # This depends on session-manager-plugin
    # brew install session-manager-plugin
    profile=${1:?missing profile}
    node=${2:?missing node}

    instance_id=$(node2id $profile $node)

    if [ -n "$instance_id" ]; then
        aws ssm start-session --target $instance_id --document-name AWS-StartInteractiveCommand --parameters command="bash -l" --profile $profile
    else
        echo "Instance not found"
    fi
}
