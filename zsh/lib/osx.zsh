if [[ "$(uname)" == "Darwin" ]]; then
  # Fix locale in ssh sessions
  export LC_ALL=en_US.UTF-8
  # Use OpenSSL installed with homebrew
  export PATH="/usr/local/opt/openssl/bin:$PATH"
fi
