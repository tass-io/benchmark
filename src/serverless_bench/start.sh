#!/bin/bash

cd $(dirname $0)

# # exec serverless_bench aws tests

# cd ./test-3-long-chain/aws/chained

# # python3 start.py

# cd ../../..

# cd ./test-5-data-transfer/aws/param-pass

# # python3 start.py

# cd ../../..

# cd ./test-6n7-hello-world/aws/hello

# # python3 start.py

# cd ../../..

# cd ./test-11-real-world/aws/azure

# # python3 start.py

# cd ../../..

# -------------------------------------

# exec serverless_bench openwhisk tests

# cd ./test-3-long-chain/openwhisk/chained

# ./eval.sh

# cd ../../..

# cd ./test-5-data-transfer/openwhisk/param-pass

# ./start.sh

# cd ../../..

# cd ./test-6n7-hello-world/openwhisk/hello

# ./eval.sh

# cd ../../..

# cd ./test-11-real-world/openwhisk/azure

# python3 RealWorldAppEmulation.py

# cd ../../..

# --------------------------------

# exec serverless_bench tass tests

cd ./test-3-long-chain/tass

python3 ./start.py

cd ../..

cd ./test-5-data-transfer/tass

python3 ./start.py

cd ../..

cd ./test-6n7-hello-world/tass

python3 ./start.py

cd ../..

cd ./test-11-real-world/tass

python3 RealWorldAppEmulation.py

cd ../..