# dev-utls

### Install

```sh
# Add in your ~/.zshrc
alias cfc='cd ~/code/cs.cfc_connect'
alias devutils='cd ~/code/dev-utils'
alias ja='~/code/dev-utils/.direnv/python-3.8.0/bin/python ~/code/dev-utils/bin/ja'
```

```sh
pyenv install 3.8.0
# if this fails then
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# after success do
git clone
cd dev-utils
direnv allow
pip install -r requirements.txt
# done
```

### Usage

```sh
usage: ja [-h] [--verbose] [--create-pr] [--how] [--open OPEN]

Dev cli helper

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         Show more information
  --create-pr, -c       Generate link to create a PR to be merged on the
                        latest release branch
  --how                 Fetches the description from the jira ticket
  --open OPEN, -o OPEN  Open either github or jira
```
