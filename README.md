# dotfiles

These are my dotfiles managed with [GNU Stow](https://www.gnu.org/software/stow/).

## Installation

install brew
git clone dotfiles

```shell
brew bundle
stow alacritty
stow git
stow tmux
stow vim
stow zsh
```

### tmux

Install TPM

```
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

## Troubleshooting

### Nvim

To fix MarkdownPreview:

```
:call mkdp#util#install()
```
