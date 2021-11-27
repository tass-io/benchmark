#!/bin/bash

cd $(dirname $0)
source "../script-config"

set -x 
set -e

ls ${SRC} | 
while IFS= read -r BENCH; do 
    ls ${SRC}/${BENCH} | 
    while IFS= read -r CASE; do 
        CODE="${SRC}/${BENCH}/${CASE}/aws" 
        rm -f ${CODE}/main ${CODE}/code.zip
    done
done
