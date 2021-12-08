# dev-utls

## 1. Dependencies

### 1.1 pyenv

- https://github.com/pyenv/pyenv#installation

### 1.2 direnv

- https://direnv.net/docs/installation.html

## 2. Installation

### 2.1 Setup Aliases

```sh
echo "alias devutils='cd ~/code/dev-utils'" >> ~/.zshrc
echo "alias ja='~/code/dev-utils/.direnv/python-3.8.2/bin/python ~/code/dev-utils/bin/ja'" >> ~/.zshrc
```

### 2.2 Install pythhon version

```sh
pyenv install 3.8.2
```

### 2.3 Clone and install project dependencies

```sh
git clone git@github.com:g3org3/dev-utils.git ~/code/dev-utils
cd ~/code/dev-utils

direnv allow
pip install -r requirements.txt
```

## 3. Usage

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
