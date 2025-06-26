#!/usr/bin/env bash
set -euo pipefail

echo "setting up venv for Python 3.9"

# load pyenv
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
eval "$(pyenv virtualenv-init -)"

# check Python 3.9 installed under pyenv
PY_VERSION=3.9.23
pyenv install -s $PY_VERSION
pyenv shell $PY_VERSION

# create venv with pyenv version
rm -rf venv
python -m venv venv

# activate
if [[ "$OSTYPE" =~ msys|cygwin ]]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi

pip install --upgrade pip
pip install -r requirements.txt

echo "Done! now running $(python --version)"
echo "To reactivate venv later: source venv/bin/activate"

