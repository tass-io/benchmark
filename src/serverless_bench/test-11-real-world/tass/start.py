import os, time, csv, yaml, random, threading, subprocess, json
import utils
from itertools import repeat

# Constant parameters
SECONDS_OF_A_DAY=3600 * 24
MILLISECONDS_PER_SECOND = 1000
mutex = threading.Lock()

TOTAL_RUN_TIME = 86400
RESULT_FILENAME = "invokeResult.csv"
SAMPLE_NUM = 30
MANUAL_SAMPLE_GENERATION = False

chainLenSampleList = [1, 1, 6, 3, 1, 1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 20, 8, 1, 2, 5, 3, 1, 2, 1, 3, 1, 2, 1]
avgIATArr = [86400.00,561.04,298.96,3927.27,293.88,77.63,4320.00,180.00,900.00,604.20,5760.00,43200.00,2700.00,28800.00,179.63,86400.00,4.52,286.09,1107.69,2.73,3600.00,86400.00,128.38,17280.00,86400.00,43200.00,1309.09,59.96,1515.79,10.00]
cvArr = [0.00,2.58,0.47,0.00,0.01,0.00,0.05,0.24,0.00,0.75,1.62,3.23,0.49,19.99,2.46,11.96,3.05,1.60,1.62,3.43,0.00,0.80,0.67,11.42,0.00,0.36,3.00,3.10,0.00,0.79]

param_schema = {
    "workflowName": "bench-04-azure",
    "flowName": "",
    "parameters": {}
}
errors = 0
success = True

def wait():
    time.sleep(20)

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

def clear_all():
    cmd("tass-cli function list | grep bench | awk '{print $2}' | xargs -n1 -I{} -P0 tass-cli function delete -n {}")
    cmd("kubectl get workflow | grep bench | awk '{print $1}' | xargs -n1 -I{} -P0 kubectl delete workflow {}")
    wait()

def post_json(url, data, appName):
    ps = param_schema.copy()
    ps['parameters'] = data
    ps['workflowName'] = appName
    return scmd("curl --max-time 900 -s -S --header \"Content-Type: application/json\" --request POST --data-raw \'%s\' \"%s\"" %(json.dumps(ps), url))

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

# Invoke apps according to the IATSeries
def Invoke(appName, results):
    id = int(appName[:])
    
    avgIAT = avgIATArr[id]
    cv = cvArr[id]

    param = {
        "seed" : id << 10
    }

    appName = 'bench-04-azure%s' %appName

    result = {"avgIAT": avgIAT, "cv": cv, "latencies": [], "rss": [], "status": []}
    print("Start to invoke App %s, avgIAT: %.2f, cv: %.2f" %(appName, avgIAT, cv))

    testTime = TOTAL_RUN_TIME
    
    mutex.acquire()
    results[appName] = result
    mutex.release()

    # Actually the while loop will be break inside
    while(testTime > 0):
        startTime = utils.getTime()
        print("[Emulate] app %s invoke, time remains: %d s" %(appName, testTime))
        param['seed'] += 1
        status, latency, rs = callInvoke(appName, param)
        result['latencies'].append(latency)
        result['rss'].append(rs)
        result['status'].append(status)
        IAT = getRandomIAT(avgIAT, cv, param['seed'])
        endTime = utils.getTime()
        testTime -= (IAT + int((endTime - startTime) / MILLISECONDS_PER_SECOND))
        if testTime < 0:
            break
        else:
            time.sleep(IAT)
    print("App %s finish testing" %(appName))
    
    return

def parseTime(timeStr):
    res = -1
    if timeStr[-2:] == '??s':
        res = int(float(timeStr[:-2]))
    elif timeStr[-2:] == 'ms':
        res = int(float(timeStr[:-2]) * 1000) 
    elif timeStr[-1:] == 's':
        res = int(float(timeStr[:-1]) * 1000 * 1000) 
    elif timeStr[-1:] == 'm':
        res = int(float(timeStr[:-1]) * 1000 * 1000 * 60) 
    else:
        raise ValueError('Not supported time end from %s' %(timeStr))
    return res

# Directly call the target application, return the latency
def callInvoke(appName, param):
    global errors
    try:
        host=sscmd("kubectl get svc %s | grep %s | awk '{print $3}'" %(appName, appName))[:-1]
        res = json.loads(post_json('http://%s/v1/workflow/' %(host), param, appName))
        execTime = parseTime(res["time"])
        status = res['success']
        if status != success:
            print("ERROR OCCURED ", res)
            errors += 1
        return status, execTime, res
    except Exception as e:
        print(e)
        errors += 1
        return False, -1, -1

# main function
def generateInvokes():
    clear_all()
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
        #chainLenSampleList = sampleGenerator.chainLenSampleListGen(SAMPLE_NUM)
        sampleGenerator.sampleActionGen(chainLenSampleList)
        print("Sample generation completes")
        print("-----------------------\n")
    resultFile = open(RESULT_FILENAME, "w")
    resultFile.write("appName@avgIAT@cv@latencies(??s)@status@rss\n")
    threads = []
    results = {}

    testStartTime = utils.getTime()
    for i in range(SAMPLE_NUM):
        appName = "%d" %i
        t = threading.Thread(target=Invoke,args=(appName,results))
        threads.append(t)

    for i in range(SAMPLE_NUM):
        threads[i].start()

    for i in range(SAMPLE_NUM):
        threads[i].join()   

    for appName, result in results.items():
        resultFile.write("%s@%.2f@%.2f@%s@%s@%s\n" %(appName, result['avgIAT'], result['cv'], str(result['latencies'])[1:-1], str(result['status'][1:-1]),str(result['rss'])[1:-1]))
    
    resultFile.close()
    testEndTime = utils.getTime()
    print("-----------------------")
    print("ERRORS: ", errors)
    duration = (testEndTime - testStartTime) / MILLISECONDS_PER_SECOND
    print("Test duration: %.2f s" %duration)
    print("Test finished")

if __name__ == "__main__":
    generateInvokes()