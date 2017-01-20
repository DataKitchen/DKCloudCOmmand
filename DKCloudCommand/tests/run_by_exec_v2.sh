#!/usr/bin/env bash

if [ -f "$HOME/venv/bin/activate" ];
then
    source $HOME/venv/bin/activate
fi
../cli/dk kitchen-list
