alias ecrlogin="aws ecr get-login-password --region us-east-1 --profile invisionapp-root | docker login --username AWS --password-stdin 416817738788.dkr.ecr.us-east-1.amazonaws.com"
alias s3="aws s3 --profile invisionapp-root"


function cluster2account() {
  cluster=$1

  case $cluster in
    use1-prev-1 | use1-prod-1)
      echo 'invisionapp-root'
      ;;
    use1-prev-2 | use1-prod-2 | use1-prod-3 | use1-prod-4 | use1-prod-5 | use1-prod-6 | use1-prod-7 | use1-prod-8 | use1-prod-9 | use1-prod-10)
      echo 'invisionapp-pc1'
      ;;
    use1-prod-11 | use1-prod-12 | use1-prod-13 | use1-prod-14)
      echo 'invisionapp-pc2'
      ;;
    use1-test-*)
      echo 'invisionapp-testing'
      ;;
  esac
}

function node2id() {
  profile=${1:?missing profile}
  node=${2:?missing node}

  if echo $node | grep -q "ec2.internal"; then
    id=$(aws ec2 describe-instances --region us-east-1 --filters Name="network-interface.private-dns-name",Values="$node" --profile $profile | jq -r '.Reservations[].Instances[].InstanceId')
  else
    id=$(aws ec2 describe-instances --region us-east-1 --filters Name="network-interface.private-ip-address",Values="$node" --profile $profile | jq -r '.Reservations[].Instances[].InstanceId')
  fi
  echo $id
}

function terminate-instance() {
  profile=${1:?missing profile}
  instance_id=${2:?missing instance_id}

  aws ec2 terminate-instances --instance-ids $instance_id --profile $profile --region us-east-1
}

function ssm-session() {
  profile=${1:?missing profile}
  node=${2:?missing node}

  instance_id=$(node2id $profile $node)

  if [ -n "$instance_id" ]; then
    aws ssm start-session --target $instance_id --document-name AWS-StartInteractiveCommand --parameters command="bash -l" --profile $profile
  else
    echo "Instance not found"
  fi
}

function cordon-node() {
  cluster=${1:?missing cluster}
  node=${2:?missing node}

  kubectl --context $cluster cordon $node
}

function drain-node() {
  cluster=${1:?missing cluster}
  node=${2:?missing node}

  kubectl --context $cluster drain --force --ignore-daemonsets --delete-local-data --timeout=180s $node
}
