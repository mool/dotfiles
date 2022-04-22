# AWS config
export AWS_SDK_LOAD_CONFIG=1

# Terraform
alias ti='terraform init'
alias tap='terraform apply'
alias tapw='terraform apply --var-file=workspaces/$(terraform workspace show).tfvars.json'
alias td='terraform destroy'
alias tdw='terraform destroy --var-file=workspaces/$(terraform workspace show).tfvars.json'
alias tp='terraform plan'
alias tpw='terraform plan --var-file=workspaces/$(terraform workspace show).tfvars.json'
alias twl='terraform workspace list'

function tws() {
  terraform workspace select $1 && direnv reload
}
