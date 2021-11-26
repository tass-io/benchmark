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

import random, json
import utils
import time
import threading
import os, subprocess

# Constant parameters
SECONDS_OF_A_DAY=3600 * 24
MILLISECONDS_PER_SECOND = 1000

# Configuration
# Warning:: SAMPLE_NUM needs to be modified in sampleGenerator.py too
TOTAL_RUN_TIME = 86400
RESULT_FILENAME = "invokeResult.csv"
SAMPLE_NUM = 30
MANUAL_SAMPLE_GENERATION = False

name = "bench-04-azure"
param = "--param seed %d"
success_status = True
cli_success_status = "ok"
errors = 0
mutex = threading.Lock()

chainLenSampleList = [1, 1, 6, 3, 1, 1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 20, 8, 1, 2, 5, 3, 1, 2, 1, 3, 1, 2, 1]
avgIATArr = [86400.00,561.04,298.96,3927.27,293.88,77.63,4320.00,180.00,900.00,604.20,5760.00,43200.00,2700.00,28800.00,179.63,86400.00,4.52,286.09,1107.69,2.73,3600.00,86400.00,128.38,17280.00,86400.00,43200.00,1309.09,59.96,1515.79,10.00]
cvArr = [0.00,2.58,0.47,0.00,0.01,0.00,0.05,0.24,0.00,0.75,1.62,3.23,0.49,19.99,2.46,11.96,3.05,1.60,1.62,3.43,0.00,0.80,0.67,11.42,0.00,0.36,3.00,3.10,0.00,0.79]

def sscmd(cmd):
    return subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout

def cmd(cmd):
    print(cmd)
    res = sscmd(cmd)
    print(res)
    return res

def scmd(cmd):
    print(cmd)
    return sscmd(cmd)

# get random IAT according to the IAT csv
def getRandAvgIAT():
    IATCDFFile = os.path.join(os.path.dirname(__file__),'CDFs','invokesCDF.csv')
    invokeTime = utils.getRandValueRefByCDF(IATCDFFile)
    IAT = SECONDS_OF_A_DAY / invokeTime
    return IAT

# get random cv according to the CSV
def getRandCV():
    cvCDFFile = os.path.join(os.path.dirname(__file__),'CDFs','CVs.csv')
    cv = utils.getRandFloatRefByCDF(cvCDFFile)
    return cv

# getIATSeries according to the avgIAT value and given cv
def getRandomIAT(avgIAT, cv, seed):
    mutex.acquire()
    random.seed(seed)
    # generate a Gauss distributed series according to the avgIAT and cv
    standardDeviation  = avgIAT * cv
    while(True):
        IAT = random.gauss(avgIAT, standardDeviation)

        # TODO: we can only accept IAT > 0, which may let avgIAT and cv 
        # deviate from the expected value 
        if IAT > 0:
            mutex.release()
            return IAT


# Invoke apps according to the IATSeries
def Invoke(appName, results):
    id = int(appName[len(name):])

    avgIAT = avgIATArr[id]
    cv = cvArr[id]

    seed = id << 10

    result = {"avgIAT": avgIAT, "cv": cv, "execTimes": [], "waitTimes": [], "status": [], "rss": []}
    print("Start to invoke App %s, avgIAT: %.2f, cv: %.2f" %(appName, avgIAT, cv))

    testTime = TOTAL_RUN_TIME
    
    # Actually the while loop will be break inside
    while(testTime > 0):
        startTime = utils.getTime()
        print("[Emulate] app %s invoke, time remains: %d s" %(appName, testTime))
        seed += 1
        status, execTime, waitTime, res = callInvoke(appName, seed)
        result['execTimes'].append(execTime)
        result['waitTimes'].append(waitTime)
        result['status'].append(status)
        result['rss'].append(res)
        endTime = utils.getTime()
        IAT = getRandomIAT(avgIAT, cv, seed)
        testTime -= (IAT + int((endTime - startTime) / MILLISECONDS_PER_SECOND))
        if testTime < 0:
            break
        else:
            time.sleep(IAT)
    print("App %s finish testing" %(appName))
    
    mutex.acquire()
    results[appName] = result
    mutex.release()
    return

# Directly call the target application, return the latency
def callInvoke(appName, seed):
    global errors
    try:
        res = scmd("wsk -i action invoke %s %s -b" %(appName, param %(seed)))
        cli_status = res.split("\n",1)[0].split(" ",1)[0][:-1]
        if cli_status != cli_success_status:
            print(res)
            raise Exception('cli_status == %s' %cli_status)
        activation = json.loads(res.split("\n",1)[-1][:-1])
        status = activation['response']['success']
        if status != success_status:
            print(res)
            raise Exception('status == %s' %(str(status)))
        result = json.dumps(activation['response']['result'])
        duration = activation['end'] - activation['start']
        waitTime = list(filter(lambda annotation: annotation['key'] == "waitTime",activation['annotations']))[0]["value"]
        return status, duration, waitTime, result
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0, 0

# main function
def generateInvokes():
    print("Test start")
    print("Total run time: %d s" %TOTAL_RUN_TIME)
    print("Result file: %s" %RESULT_FILENAME)
    print("Sample number: %d" %SAMPLE_NUM)
    print("-----------------------\n")
    
    # Automatically generate random samples
    # We suggest that generate the samples manually or automatically generate samples only once
    if not MANUAL_SAMPLE_GENERATION:
        global chainLenSampleList
        print("Generate the samples")
        import sampleGenerator
        #chainLenSampleList = sampleGenerator.chainLenSampleListGen(SAMPLE_NUM)
        sampleGenerator.sampleActionGen(chainLenSampleList)
        print("Sample generation completes")
        print("-----------------------\n")
    resultFile = open(RESULT_FILENAME, "w")
    resultFile.write("appName@avgIAT@cv@execTimes@waitTimes@status@rss\n")
    threads = []
    results = {}

    testStartTime = utils.getTime()
    for i in range(SAMPLE_NUM):
        appName = "%s%d" %(name, i)
        t = threading.Thread(target=Invoke,args=(appName,results))
        threads.append(t)

    for i in range(SAMPLE_NUM):
        threads[i].start()

    for i in range(SAMPLE_NUM):
        threads[i].join()   

    for appName, result in results.items():
        resultFile.write("%s@%.2f@%.2f@%s@%s@%s@%s\n" %(appName, result['avgIAT'], result['cv'], str(result['execTimes'])[1:-1], str(result['waitTimes'])[1:-1], str(result['status'])[1:-1], str(result['rss'])[1:-1]))
    
    resultFile.close()
    testEndTime = utils.getTime()
    print("-----------------------")
    duration = (testEndTime - testStartTime) / MILLISECONDS_PER_SECOND
    print("Test duration: %.2f s" %duration)
    print("Test finished")
    print("ERRORS REQS: %d" %errors)

if __name__ == "__main__":
    generateInvokes()
