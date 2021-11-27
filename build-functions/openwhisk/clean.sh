#!/bin/bash
# FYI: Only the codes have dependency needs to clean up

cd $(dirname $0)
source "../script-config"

CASES=("${SRC}/serverless_bench/test-5-data-transfer")

set -x 
set -e

rm -f main-bin.zip main-src.zip main.go

for CASE in "${CASES[@]}"; do
    rm -f ${CODE}/main-bin.zip
    done
done
