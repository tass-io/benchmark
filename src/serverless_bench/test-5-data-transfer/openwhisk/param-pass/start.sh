#!/bin/bash

echo "1. start origin data transfer cost..."

./single-cold_warm.sh.bk > origin.log

echo "2. start redis data transfer cost..."

./single-cold_warm.sh > redis.log
