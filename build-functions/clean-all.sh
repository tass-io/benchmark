#!/bin/bash

cd $(dirname $0)
source "./script-config"

set -e
set -x

for target in $(ls -l | awk '/^d/ {print $NF}'); do
    ./${target}/clean.sh
done
