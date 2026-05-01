export PULUMI_PARALLEL=45

export BAO_ADDR="https://openbao.ops-oma-prod.interval.team"
export VAULT_ADDR="$BAO_ADDR"
export VAULT_SERVER_URL="$BAO_ADDR"

# Add psql path
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

function gcp-login() {
  gcloud auth login
  gcloud auth application-default login
}
