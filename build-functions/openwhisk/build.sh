#!/bin/bash
# FYI: Only the codes have dependency needs to build
# FIXME: The image is only usable in AMD64 platform

cd $(dirname $0)
source "../script-config"

CASES=("${SRC}/serverless_bench/test-5-data-transfer")

set -x 
set -e

./clean.sh

for CASE in "${CASES[@]}"; do
    CODE="${CASE}/openwhisk" 
    cp ${CODE}/main.go ./
    zip main-src.zip -qr main.go go.mod go.sum
    docker run -i openwhisk/action-golang-v1.16:nightly -compile main <main-src.zip >main-bin.zip
    cp main-bin.zip ${CODE}/main-bin.zip
    done
done
