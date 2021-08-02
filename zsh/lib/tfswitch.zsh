load-tfswitch() {
  local tfswitch_path=".tfswitch"
  local tfswitchrc_path=".tfswitchrc"

  if [[ -f "$tfswitchrc_path" || -f "$tfswitch_path" ]]; then
    tfswitch
  fi
}

add-zsh-hook chpwd load-tfswitch
load-tfswitch
