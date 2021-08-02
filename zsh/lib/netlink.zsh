function nssh() {
  ssh admin@$1 -L 8080:192.168.1.2:80 -L 8081:192.168.0.1:80
}
