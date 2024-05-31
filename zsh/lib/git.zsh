function gpc() {
  git pull && git cleanup
}

function gpdel() {
  main_branch=$(git mb)
  git pull && git delete-squashed $main_branch
}

function gcom() {
  git checkout $(git mb)
}
