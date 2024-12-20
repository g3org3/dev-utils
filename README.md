# dev-utils

## 1. Dependencies

### 1.1 pyenv

- https://github.com/pyenv/pyenv#installation

### 1.2 direnv

- https://direnv.net/docs/installation.html

## 2. Installation

### 2.1 Setup Aliases

```sh
echo "alias devutils='cd ~/code/dev-utils'" >> ~/.zshrc
echo "alias ja='~/code/dev-utils/.direnv/python-3.9/bin/python ~/code/dev-utils/bin/ja'" >> ~/.zshrc
```

### 2.2 Install python version

```sh
sudo pwd
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget
```

```sh
pyenv install 3.9.7
```

### 2.3 Clone and install project dependencies

```sh
git clone git@github.com:g3org3/dev-utils.git ~/code/dev-utils
cd ~/code/dev-utils
```

```sh
direnv allow
pip install --upgrade pip; pip install -r requirements.txt
```

## 3. Usage

```sh
ja
```
