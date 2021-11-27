#!/bin/bash

cd $(dirname $0)
source "../script-config"

set -x 
set -e

ls ${SRC} | 
while IFS= read -r BENCH; do 
    ls ${SRC}/${BENCH} | 
    while IFS= read -r CASE; do 
        ls ${SRC}/${BENCH}/${CASE}/tass/function |
        while IFS= read -r FUNC; do
            CODE="${SRC}/${BENCH}/${CASE}/tass/function/${FUNC}" 
            rm -f ${CODE}/plugin.so
        done
    done
done
