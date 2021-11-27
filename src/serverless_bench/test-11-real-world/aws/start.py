import os, time, csv, random, threading, subprocess, json, sys
from sampleGenerator import create_json_file
import utils

name = "bench-04-azure"

func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
log_name_prefix = '/aws/vendedlogs/states/'
exec_log_filter= 'fields @message | filter @message like /(?i)(ExecutionStarted|ExecutionSucceeded)/'
log_interval=2700 # 45min
errors = 0
succ_status = 'SUCCEEDED'
log_succ_status = 'Complete'
mutex = threading.Lock()
all_done = False

def wait():
    time.sleep(75 + 75 *random.random()/10)

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

def jcmd(cmd):
    output = scmd(cmd)
    parsingDone = False
    res = {}
    while not parsingDone:
        try:
            res = json.loads(output)
            parsingDone = True
        except Exception as e:
            print("cmd %s parsing jsong error, get res: %s, the exception: %s" %(cmd, output, str(e)))
            wait()
    return res

def jecmd(cmd, assertion, expStr):
    res = {}
    assertionDone = False
    while not assertionDone:
        try:
            res = jcmd(cmd)
            if not assertion(res):
                raise Exception(expStr)
            assertionDone = True
        except Exception as e:
            print("ASSERTION ERROR!!", e, "RESULT:", res)
            time.sleep(20 + 20*random.random()/10)
    return res
    
# Constant parameters
SECONDS_OF_A_DAY=3600 * 24
MILLISECONDS_PER_SECOND = 1000

TOTAL_RUN_TIME = 86400
RESULT_FILENAME = "result.csv"
SAMPLE_NUM = 30
MANUAL_SAMPLE_GENERATION = False

chainLenSampleList = [1, 1, 6, 3, 1, 1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 20, 8, 1, 2, 5, 3, 1, 2, 1, 3, 1, 2, 1]
avgIATArr = [86400.00,561.04,298.96,3927.27,293.88,77.63,4320.00,180.00,900.00,604.20,5760.00,43200.00,2700.00,28800.00,179.63,86400.00,4.52,286.09,1107.69,2.73,3600.00,86400.00,128.38,17280.00,86400.00,43200.00,1309.09,59.96,1515.79,10.00]
cvArr = [0.00,2.58,0.47,0.00,0.01,0.00,0.05,0.24,0.00,0.75,1.62,3.23,0.49,19.99,2.46,11.96,3.05,1.60,1.62,3.43,0.00,0.80,0.67,11.42,0.00,0.36,3.00,3.10,0.00,0.79]

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
    # return float(np.random.normal(avgIAT, standardDeviation, 1)[0])
    while(True):
        IAT = random.gauss(avgIAT, standardDeviation)

        # TODO: we can only accept IAT > 0, which may let avgIAT and cv 
        # deviate from the expected value 
        if IAT > 0:
            mutex.release()
            return IAT

def get_res_from_log(result, metaStart):
    start = metaStart
    arnMap = result['arnMap']
    while len(arnMap) != 0:
        if len(arnMap) <= 1:
            wait()
            continue
        # assure logs are completed logged
        queryRes = jecmd("""aws logs start-query --profile linxuyalun --limit 10000 \
        --log-group-name '%s%s%d' \
        --start-time '%d' \
        --end-time '%d' \
        --query-string '%s'""" %(log_name_prefix, name, result['id'], start-log_interval*2, (utils.getTime() / MILLISECONDS_PER_SECOND) + log_interval*2, exec_log_filter)
            , lambda j: ("queryId" in j.keys()), "Creating query invoke result has no queryId")
        res = jecmd("aws logs get-query-results --profile linxuyalun --query-id '%s'" %queryRes['queryId']
            , lambda j: (j['status'] == log_succ_status), "The log result is not ready")
        # get execution time of the whole stepfunctions
        msgs = list(map(lambda result: json.loads(list(filter(lambda field: field['field'] == '@message', result))[0]['value']), res['results']))
        toDeleteArn = []
        hasTouch = False
        for msg in msgs:
            arn = msg['execution_arn']
            ts = int(msg['event_timestamp'])
            if ts > start:
                start = ts
            if arn in arnMap.keys():
                invoke = arnMap[arn]
                touch = False
                if msg['type'] == 'ExecutionStarted':
                    invoke['ExecutionStarted'] = ts
                    touch = True
                elif msg['type'] == 'ExecutionSucceeded':
                    invoke['ExecutionSucceeded'] = ts
                    touch = True
                else: 
                    raise Exception("ERROR!!! what the fuck is this messgae type? %s" %msg['type'])
                if touch:
                    hasTouch = True
                    if 'ExecutionSucceeded' in invoke.keys() and 'ExecutionStarted' in invoke.keys():
                        invoke['execTime'] = invoke['ExecutionSucceeded'] - invoke['ExecutionStarted']
                        del invoke['ExecutionSucceeded']
                        del invoke['ExecutionStarted']
                        toDeleteArn.append(arn)
                        print("I'm done!")
        for arn in toDeleteArn:
            del arnMap[arn]
        if not hasTouch:
            print("WTF?!?!?!? ID%d no logs touching!!!!!" %(result['id']))
            start = metaStart # TODO
        if len(arnMap) > 1:
            print("ID%d has %d logs are waiting" %(result['id'], len(arnMap) - 1))
        time.sleep(log_interval + log_interval * random.random() / 10)
        
# Invoke apps according to the IATSeries
def Invoke(appName, results):

    id = int(appName[len(name):])
    param = {
        "seed": id << 10
    }
    
    avgIAT = avgIATArr[id]
    cv = cvArr[id]

    result = {"avgIAT": avgIAT, "cv": cv, "invokes": [], "arnMap": {"finish": False}, "id": id}
    t = threading.Thread(target=get_res_from_log,args=[result,(utils.getTime() / MILLISECONDS_PER_SECOND)])
    t.start()

    mutex.acquire()
    results[appName] = result
    mutex.release()

    print("Start to invoke App %s, avgIAT: %.2f, cv: %.2f" %(appName, avgIAT, cv))

    testTime = TOTAL_RUN_TIME
    
    # Actually the while loop will be break inside
    while(testTime > 0):
        startTime = utils.getTime()
        print("[Emulate] app %s invoke, time remains: %d s" %(appName, testTime))
        param['seed'] += 1
        invoke = callInvoke(appName, json.dumps(param), result["arnMap"])
        result['invokes'].append(invoke)
        IAT = getRandomIAT(avgIAT, cv, param['seed'])
        endTime = utils.getTime()
        testTime -= (IAT + int((endTime - startTime) / MILLISECONDS_PER_SECOND))
        if testTime < 0:
            break
        else:
            time.sleep(IAT)

    while len(result['arnMap']) != 1:
        wait()
    del result["arnMap"]["finish"]
    t.join()
    print("App %s finish testing" %(appName))

# Directly call the target application, return the latency
def callInvoke(appName, param, arnMap):
    global errors
    res = {}
    try:
        res = scmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, appName, param))
        res = json.loads(res)
        status = res['status']
        if status != succ_status:
            errors = errors + 1
            print(status)
            return {"status": status, "rs": res, "execTime": "FAILED"}
        else:
            execArn = res['executionArn']
            output = json.dumps(json.loads(res['output']))
            res = {"status": status, "rs": output, "execArn": execArn}
            arnMap[execArn] = res
            return res
    except Exception as e:
        errors = errors + 1
        print("UNEXPECTED FAILED", e, res)
        return {"status": "UNEXPECTED FAILED", "rs": res, "execTime": "UNEXPECTED FAILED"}

def printResults(results, atOnce, path):
    while not all_done:
        sscmd("mv %s %s.copy" %(path, path))
        create_json_file(results, path)
        if atOnce:
            return
        wait()

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
        print("Generate the samples")
        import sampleGenerator
        # chainLenSampleList = sampleGenerator.chainLenSampleListGen(SAMPLE_NUM)
        sampleGenerator.sampleActionGen(chainLenSampleList)
        print("Sample generation completes")
        print("-----------------------\n")
    resultFile = open(RESULT_FILENAME, "w")
    resultFile.write("appName@avgIAT@cv@latencies@status@rss\n")
    threads = []
    results = {}

    testStartTime = utils.getTime()
    for i in range(SAMPLE_NUM):
        appName = "%s%d" %(name, i)
        t = threading.Thread(target=Invoke,args=[appName,results])
        threads.append(t)

    for thread in threads:
        thread.start()

    t = threading.Thread(target=printResults,args=[results, False, "./results"])
    tt = threading.Thread(target=printResults,args=[{"len": len(results)}, False, "./results-len"])
    t.start()
    tt.start()
    for thread in threads:
        thread.join() 

    global all_done
    all_done = True  

    t.join()
    tt.join()

    t = threading.Thread(target=printResults,args=[results, True, "./results"])
    t.start()
    t.join()

    tt = threading.Thread(target=printResults,args=[{"len": len(results)}, False, "./results-len"])
    tt.start()
    tt.join()

    for appName, result in results.items():
        resultFile.write("%s@%.2f@%.2f@%s@%s@%s\n" %(appName, result['avgIAT'], result['cv'], str(list(map(lambda invoke: invoke['execTime'], result['invokes']))[1:-1]),  str(list(map(lambda invoke: invoke['status'], result['invokes']))[1:-1]), str(list(map(lambda invoke: invoke['rs'], result['invokes']))[1:-1])))    
        
    resultFile.close()

    t = threading.Thread(target=printResults,args=[results, True, "./results-with-log"])
    t.start()
    t.join()

    testEndTime = utils.getTime()
    print("-----------------------")
    duration = (testEndTime - testStartTime) / MILLISECONDS_PER_SECOND
    print("Test duration: %.2f s" %duration)
    print("Test finished")
    print("ERRORS REQS: %d" %errors)

if __name__ == "__main__":
    generateInvokes()
