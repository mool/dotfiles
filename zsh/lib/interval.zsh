export PULUMI_PARALLEL=45

function gcp-login() {
  gcloud auth login
  gcloud auth application-default login
}
