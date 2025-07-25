#/bin/bash

# Disable natural scrolling
defaults write NSGlobalDomain com.apple.swipescrolldirection -bool false

# Don’t automatically rearrange Spaces based on most recent use
defaults write com.apple.dock mru-spaces -bool false

# Screenshots
SCREENSHOTS_PATH=${HOME}/Desktop/screenshots
mkdir -p ${SCREENSHOTS_PATH}
defaults write com.apple.screencapture location -string "${SCREENSHOTS_PATH}"

# Chrome Settings
# defaults write com.google.Chrome ExternalProtocolDialogShowAlwaysOpenCheckbox -bool true
