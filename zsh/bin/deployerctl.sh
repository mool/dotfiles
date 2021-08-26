#!/bin/bash
# Usage:
#   deployerctl.sh testing diff
#   deployerctl.sh testing apply -d
#   deployerctl.sh testing apply
#   deployerctl.sh multi-tenant apply

TIER=${1:?missing arg1: tier}; shift
CMD="${@:?missing arg2: cmd <diff | apply -d | apply >}"

set -x
deployerctl -p . -r $(basename $(pwd -L)) -s $(git rev-parse HEAD) -b $(git branch --show-current) -t "${TIER}" ${CMD}
