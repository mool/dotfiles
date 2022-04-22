export ZPLUG_HOME=$(brew --prefix zplug)
source $ZPLUG_HOME/init.zsh

zplug "lib/completion",          from:oh-my-zsh
zplug "lib/directories",          from:oh-my-zsh
zplug "lib/grep",                 from:oh-my-zsh
zplug "lib/history",              from:oh-my-zsh
zplug "lib/key-bindings",         from:oh-my-zsh
zplug "lib/theme-and-appearance", from:oh-my-zsh

zplug "plugins/aws",            from:oh-my-zsh
zplug "plugins/docker",         from:oh-my-zsh
zplug "plugins/docker-compose", from:oh-my-zsh
zplug "plugins/git",            from:oh-my-zsh
zplug "plugins/helm",           from:oh-my-zsh
zplug "plugins/kubectl",        from:oh-my-zsh
zplug "plugins/macos",          from:oh-my-zsh
zplug "plugins/terraform",      from:oh-my-zsh

# zplug "zsh-users/zsh-completions",         from:github
zplug "zsh-users/zsh-syntax-highlighting", from:github, defer:3

# Let zplug manage zplug
zplug 'zplug/zplug', hook-build:'zplug --self-manage'

zplug "spaceship-prompt/spaceship-prompt", as:theme

# Install plugins if there are plugins that have not been installed
if ! zplug check --verbose; then
    printf "Install? [y/N]: "
    if read -q; then
        echo; zplug install
    fi
fi

zplug load
