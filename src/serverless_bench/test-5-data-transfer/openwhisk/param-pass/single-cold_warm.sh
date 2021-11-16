#!/bin/bash
#
# Copyright (c) 2020 Institution of Parallel and Distributed System, Shanghai Jiao Tong University
# ServerlessBench is licensed under the Mulan PSL v1.
# You can use this software according to the terms and conditions of the Mulan PSL v1.
# You may obtain a copy of Mulan PSL v1 at:
#     http://license.coscl.org.cn/MulanPSL
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v1 for more details.
#

Sizesdic=(1048576 2097152 4194304 8388608 16777216)
#Sizesdic=(0)

./action_update.sh

if [[ ! -d ./payload ]]
then
    mkdir payload
fi

if [[ ! -d ./test-results ]]
then
    mkdir test-results
fi

# exec cold tests
python3 payloadCreater.py 0
COLD_LOG="test-results/Result-Cold-0.csv"
COLD_TIMES=0
PAYLOADFILE=payload/payload_0.json
LATENCYSUM=0
if [[ ! -e $COLD_LOG ]]; then
    echo "cold logfile $COLD_LOG does not exist, create it"
    touch $COLD_LOG
fi

for i in $(seq 1 $COLD_TIMES)
do
    # wait untill all container releases
    while [[ -n `kubectl get pod -A | grep wskowdev-invoker | awk '{print 2}'` ]]; do sleep 1; done
    # exec tests
    invokeTime=`date +%s%3N`
    rawres=`wsk -i action invoke ParamPassSeq --param payload redis  --blocking --result` 
    latency=`echo $rawres | jq -r '.comTime'`
    echo $latency
    echo $rawres
    echo $latency >> $COLD_LOG
    LATENCYSUM=`expr $latency + $LATENCYSUM`
    LATENCIES[$i]=$latency
    echo "cold time $i finished"
done

# Sort the latencies
for((i=0; i<$COLD_TIMES+1; i++)){
for((j=i+1; j<$COLD_TIMES+1; j++)){
    if [[ ${LATENCIES[i]} -gt ${LATENCIES[j]} ]]
    then
    temp=${LATENCIES[i]}
    LATENCIES[i]=${LATENCIES[j]}
    LATENCIES[j]=$temp
    fi
    if [[ ${STARTS[i]} -gt ${STARTS[j]} ]]
    then
    temp=${STARTS[i]}
    STARTS[i]=${STARTS[j]}
    STARTS[j]=$temp
    fi
}
}

echo "------------------ result ---------------------" >> $COLD_LOG
_50platency=${LATENCIES[`echo "$COLD_TIMES * 0.5"| bc | awk '{print int($0)}'`]}
_75platency=${LATENCIES[`echo "$COLD_TIMES * 0.75"| bc | awk '{print int($0)}'`]}
_90platency=${LATENCIES[`echo "$COLD_TIMES * 0.90"| bc | awk '{print int($0)}'`]}
_95platency=${LATENCIES[`echo "$COLD_TIMES * 0.95"| bc | awk '{print int($0)}'`]}
_99platency=${LATENCIES[`echo "$COLD_TIMES * 0.99"| bc | awk '{print int($0)}'`]}
echo "Communicate Latency (ms):" >> $COLD_LOG
echo -e "Avg\t50%\t75%\t90%\t95%\t99%\t" >> $COLD_LOG
AVGLAT=`awk 'BEGIN{printf "%.2f\n",'$LATENCYSUM'/'$COLD_TIMES'}'`
echo -e "$AVGLAT\t$_50platency\t$_75platency\t$_90platency\t$_95platency\t$_99platency\t" >> $COLD_LOG


# warm tests
for payload_size in ${Sizesdic[@]}
do
    TIMES=100
    WARMUP_TIMES=5
    LATENCYSUM=0
    LOGFILE="test-results/Result-$payload_size.csv"
    
    # Create payload file
    python3 payloadCreater.py $payload_size
    PAYLOADFILE=payload/payload_$payload_size.json
    echo "Payload size: $payload_size"
    echo "Log file: $LOGFILE"
    if [[ ! -e $LOGFILE ]]; then
        echo "logfile $LOGFILE does not exist, create it"
        touch $LOGFILE
    fi

    REDIS_ADDR=$(kubectl get svc -o custom-columns=IP:.spec.clusterIP redis | grep -v IP)

    for i in $(seq 1 $WARMUP_TIMES)
    do
	redis-cli -h ${REDIS_ADDR} -p 6379 -n 0 -x set param0 < ./payload/payload_$payload_size.json
        wsk -i action invoke ParamPassSeq --param payload redis  --blocking --result
        sleep 1
    done
    
    for i in $(seq 1 $TIMES)
    do
        invokeTime=`date +%s%3N`
	start_bench=`echo $(($(date +%s%N)/1000000))`
	redis-cli -h ${REDIS_ADDR} -p 6379 -n 0 -x set param0 < ./payload/payload_$payload_size.json
        rawres=`wsk -i action invoke ParamPassSeq --param payload redis  --blocking --result`
	redis-cli -h ${REDIS_ADDR} -p 6379 -n 0 get param2 > ./param2
	end_bench=`echo $(($(date +%s%N)/1000000))`
	latency="$((${end_bench} - ${start_bench}))"
        echo $latency
	echo $rawres
        echo $latency >> $LOGFILE
	wc -c ./param2
	rm -f ./param2
        LATENCYSUM=`expr $latency + $LATENCYSUM`
        LATENCIES[$i]=$latency
        echo "time $i finished"
        # one function can be called 60 times a minute
        sleep 1
    done

    rm $PAYLOADFILE

    # Sort the latencies
    for((i=0; i<$TIMES+1; i++)){
    for((j=i+1; j<$TIMES+1; j++)){
        if [[ ${LATENCIES[i]} -gt ${LATENCIES[j]} ]]
        then
        temp=${LATENCIES[i]}
        LATENCIES[i]=${LATENCIES[j]}
        LATENCIES[j]=$temp
        fi
        if [[ ${STARTS[i]} -gt ${STARTS[j]} ]]
        then
        temp=${STARTS[i]}
        STARTS[i]=${STARTS[j]}
        STARTS[j]=$temp
        fi
    }
    }

    echo "------------------ result ---------------------" >> $LOGFILE
    _50platency=${LATENCIES[`echo "$TIMES * 0.5"| bc | awk '{print int($0)}'`]}
    _75platency=${LATENCIES[`echo "$TIMES * 0.75"| bc | awk '{print int($0)}'`]}
    _90platency=${LATENCIES[`echo "$TIMES * 0.90"| bc | awk '{print int($0)}'`]}
    _95platency=${LATENCIES[`echo "$TIMES * 0.95"| bc | awk '{print int($0)}'`]}
    _99platency=${LATENCIES[`echo "$TIMES * 0.99"| bc | awk '{print int($0)}'`]}

    echo "Communicate Latency (ms):" >> $LOGFILE
    echo -e "Avg\t50%\t75%\t90%\t95%\t99%\t" >> $LOGFILE
    AVGLAT=`awk 'BEGIN{printf "%.2f\n",'$LATENCYSUM'/'$TIMES'}'`
    echo -e "$AVGLAT\t$_50platency\t$_75platency\t$_90platency\t$_95platency\t$_99platency\t" >> $LOGFILE
done
