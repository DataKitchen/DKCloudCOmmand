#!/usr/bin/env bash

ENV=DKCloudCommand
source $WORKON_HOME/$ENV/bin/activate
../cli/dk kitchen-list
