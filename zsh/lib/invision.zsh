# AWS config
export AWS_SDK_LOAD_CONFIG=1

alias ecrlogin="aws ecr get-login-password --region us-east-1 --profile invisionapp-root | docker login --username AWS --password-stdin 416817738788.dkr.ecr.us-east-1.amazonaws.com"
alias s3="aws s3 --profile invisionapp-root"

# Terraform
alias ti='terraform init --backend-config ~/InVision/platform-infra/admin.config.json'
alias tp='terraform plan --var-file '
alias tap='terraform apply --var-file '
alias twl='terraform workspace list'

function tws() {
  terraform workspace select $1 && direnv reload
}
