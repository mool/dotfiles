function gpc() {
  git pull && git cleanup
}

function gpdel() {
  main_branch=${1:-master}
  git pull && git delete-squashed $main_branch
}
