import os, requests, time, csv, yaml, random, threading, subprocess, json, sys
import utils

name = "bench-04-azure"

func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
log_name_prefix = '/aws/vendedlogs/states/'
errors = 0
succ_status = 'SUCCEEDED'
mutex = threading.Lock()

def wait():
    time.sleep(6)

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

# Constant parameters
SECONDS_OF_A_DAY=3600 * 24
MILLISECONDS_PER_SECOND = 1000

# Config parameters
config = yaml.load(open(os.path.join(os.path.dirname(__file__),'config.yaml')), yaml.FullLoader)

TOTAL_RUN_TIME = int(config['total_run_time'])
RESULT_FILENAME = config['result_file']
SAMPLE_NUM = config['sample_number']
MANUAL_SAMPLE_GENERATION = config['manual_sample_generation']

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
def getRandomIAT(avgIAT, cv):
    # generate a Gauss distributed series according to the avgIAT and cv
    standardDeviation  = avgIAT * cv
    # return float(np.random.normal(avgIAT, standardDeviation, 1)[0])
    while(True):
        IAT = random.gauss(avgIAT, standardDeviation)

        # TODO: we can only accept IAT > 0, which may let avgIAT and cv 
        # deviate from the expected value 
        if IAT > 0:
            return IAT

# Invoke apps according to the IATSeries
def Invoke(appName, results):

    id = int(appName[len(name):])
    param = json.dumps({
        "seed": id << 10
    })
    
    avgIAT = avgIATArr[id]
    cv = cvArr[id]

    result = {"avgIAT": avgIAT, "cv": cv, "invokes": []}
    print("Start to invoke App %s, avgIAT: %.2f, cv: %.2f" %(appName, avgIAT, cv))

    testTime = TOTAL_RUN_TIME
    
    # Actually the while loop will be break inside
    while(testTime > 0):
        startTime = utils.getTime()
        print("[Emulate] app %s invoke, time remains: %d s" %(appName, testTime))
        invoke = callInvoke(appName, param)
        result['invokes'].append(invoke)
        
        IAT = getRandomIAT(avgIAT, cv)
        endTime = utils.getTime()
        testTime -= (IAT + int(endTime - startTime / MILLISECONDS_PER_SECOND))
        if testTime < 0:
            break
        else:
            time.sleep(IAT)
    result['id'] = id
    print("App %s finish testing" %(appName))

    mutex.acquire()
    results[appName] = result
    mutex.release()
    return

# Directly call the target application, return the latency
def callInvoke(appName, param):
    global errors
    try:
        res = json.loads(cmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, appName, param)))
        status = res['status']
        if status != succ_status:
            errors = errors + 1
            print(status)
            return {"status": status}
        else:
            execArn = res['executionArn']
            return {"status": status, "execArn": execArn}
    except:
        return {"status": "FAILED"}

def get_res_from_log(exec_arn, id):
    # assure logs are completed logged
    all_logged = False
    while not all_logged:
        try:
            res = json.loads(sscmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s%d' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "ExecutionStarted" || $.type = "ExecutionSucceeded" ) }'""" %(log_name_prefix, name, id, exec_arn)))
            if len(res['events']) != 2:
                raise Exception("len(events) is %d rather than 2" %(len(res['events'])))
            all_logged = True
            break
        except:
            print("waiting for logging finished get err:", sys.exc_info()[0])
            wait()
    # get execution time of the whole stepfunctions
    res = json.loads(scmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s%d' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "ExecutionStarted" || $.type = "ExecutionSucceeded" ) }'""" %(log_name_prefix, name, id, exec_arn)))
    for event in res['events']: event['message'] = json.loads(event['message'])
    res['events'].sort(key=lambda event: int(event['message']['id']))
    times = list(map(lambda event: int(event['message']['event_timestamp']), res['events']))
    execTime = times[1] - times[0]
    # get each function execution time and the function path 
    res = json.loads(scmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s%d' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "LambdaFunctionScheduled" || $.type = "LambdaFunctionSucceeded" ) }'""" %(log_name_prefix, name, id, exec_arn)))
    for event in res['events']: event['message'] = json.loads(event['message'])
    res['events'].sort(key=lambda event: int(event['message']['id']))
    times = list(map(lambda event: int(event['message']['event_timestamp']), res['events']))
    funcTimes = []
    last = -1
    for t in times:
        if last != -1:
            funcTimes.append(t-last) 
        last = t
    funcPath = list(map(lambda sevent: sevent['message']['details']['resource'][len(func_arn):], filter(lambda event: event['message']['type'] == 'LambdaFunctionScheduled', res['events'])))
    return {"execTime": execTime, "funcTimes": funcTimes, "funcPath": funcPath}

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
    resultFile.write("appName@avgIAT@cv@latencies\n")
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
        result['latencies'] = []
        for invoke in result['invokes']:
            if invoke['status'] == succ_status:
                invoke.update(get_res_from_log(invoke['execArn'], result['id']))
            else:
                invoke['execTime'] = "failed"
        resultFile.write("%s@%.2f@%.2f@%s\n" %(appName, result['avgIAT'], result['cv'], str(list(map(lambda invoke: invoke['execTime'], result['invokes']))[1:-1])))
    
    resultFile.close()
    testEndTime = utils.getTime()
    print("-----------------------")
    duration = (testEndTime - testStartTime) / MILLISECONDS_PER_SECOND
    print("Test duration: %.2f s" %duration)
    print("Test finished")
    print("ERRORS REQS: %d" %errors)

if __name__ == "__main__":
    generateInvokes()