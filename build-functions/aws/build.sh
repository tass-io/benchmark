#!/bin/bash

cd $(dirname $0)
source "../script-config"

set -x 
set -e

./clean.sh

ls ${SRC} | 
while IFS= read -r BENCH; do 
    ls ${SRC}/${BENCH} | 
    while IFS= read -r CASE; do 
        CODE="${SRC}/${BENCH}/${CASE}/aws" 
        CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o ${CODE}/main ${CODE}/main.go
        cp ${CODE}/main ./
        zip code.zip -qr main
        cp code.zip ${CODE}/code.zip
    done
done
