#!/usr/bin/env bash

if [ -f "$HOME/Envs/dk/bin/activate" ];
then
    source $HOME/Envs/dk/bin/activate
fi
../cli/dk kitchen-list
