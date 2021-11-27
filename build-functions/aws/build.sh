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
        go build -o ${CODE}/main ${CODE}/main.go
        zip ${CODE}/code.zip ${CODE}/main
    done
done
