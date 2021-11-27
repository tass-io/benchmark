#!/bin/bash

cd $(dirname $0)
source "../script-config"
# WARNING: Building cross platform plugin may occur a linking issue.
#          Plz build the tass benchmark on the desired environment

set -x 
set -e

./clean.sh 

ls ${SRC} | 
while IFS= read -r BENCH; do 
    ls ${SRC}/${BENCH} | 
    while IFS= read -r CASE; do 
        ls ${SRC}/${BENCH}/${CASE}/tass/function |
        while IFS= read -r FUNC; do
            CODE="${SRC}/${BENCH}/${CASE}/tass/function/${FUNC}" 
            go build -o ${CODE}/plugin.so --buildmode=plugin ${CODE}/plugin.go
        done
    done
done
