function valid_ip() {
	local  ip=$1
	local  stat=1

	if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
		OIFS=$IFS
		IFS='.'
		ip=($ip)
		IFS=$OIFS
		[[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
			&& ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
		stat=$?
	fi
	return $stat
}

function kssh() {
	dest=$1
	if valid_ip $dest; then
		instance_info $dest --no-ssh
		ssh $dest
	else
		ip_address=$(knife search node "name:$dest" -a ipaddress|grep ipaddress|sed -e 's/ //g'|cut -d':' -f2)
		case $2 in
			"")
				echo "Connecting to $dest [$ip_address] via SSH"
				ssh $ip_address
				;;
			*)
				echo "Connecting to $dest [$ip_address] via SSH and running '$2'"
				ssh -o ConnectTimeout=10 $ip_address $2
				;;
		esac
	fi
}

source /home/mool/InVision/kubernetes-coreos/cli/setup.sh

# Required for all commands
export LOGGLY_CUSTOMER_TOKEN=***REMOVED***
export INVCTL_DATADOG_APP_KEY=xxxxxxxxxxxxxxxx
export INVCTL_DATADOG_API_KEY=***REMOVED***

# Required for using the sync or generate commands
# export KIT_ACCESS_TOKEN=

# Required for using the kube command
export KUBERNETES_COREOS_DIR="~/InVision/kubernetes-coreos"

# Required for self-updating of invctl
export AWS_ACCESS_KEY_ID=***REMOVED***
export AWS_SECRET_ACCESS_KEY=***REMOVED***

# Required for the elroy client
# export INVCTL_ELROY_URL=https://elroy-endpoint
# export INVCTL_ELROY_TOKEN=token


alias ik="invctl kube"
