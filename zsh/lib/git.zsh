function gpc() {
  git pull && git cleanup
}

function gpdel() {
  main_branch=$(git mb)
  git pull && git delete-squashed $main_branch
}

function gcob() {
  git checkout $(git branch | fzf)
}

function gcom() {
  git checkout $(git mb)
}
