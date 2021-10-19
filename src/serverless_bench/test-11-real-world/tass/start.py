import os, requests, time, csv, yaml, random, threading
import utils
from itertools import repeat

# Constant parameters
SECONDS_OF_A_DAY=3600 * 24
MILLISECONDS_PER_SECOND = 1000


# Config parameters
config = yaml.load(open(os.path.join(os.path.dirname(__file__),'config.yaml')), yaml.FullLoader)

TOTAL_RUN_TIME = int(config['total_run_time'])
RESULT_FILENAME = config['result_file']
SAMPLE_NUM = config['sample_number']
MANUAL_SAMPLE_GENERATION = config['manual_sample_generation']

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
    
    avgIAT = getRandAvgIAT()
    cv = getRandCV()

    result = {"avgIAT": avgIAT, "cv": cv, "latencies": []}
    print("Start to invoke App %s, avgIAT: %.2f, cv: %.2f" %(appName, avgIAT, cv))

    testTime = TOTAL_RUN_TIME
    
    # Actually the while loop will be break inside
    while(testTime > 0):
        print("[Emulate] app %s invoke, time remains: %d s" %(appName, testTime))
        latency = callInvoke(appName)
        result['latencies'].append(latency)
        
        IAT = getRandomIAT(avgIAT, cv)
        testTime -= (IAT + int(latency / MILLISECONDS_PER_SECOND))
        if testTime < 0:
            break
        else:
            time.sleep(IAT)
    print("App %s finish testing" %(appName))
    
    results[appName] = result
    return

# Directly call the target application, return the latency
def callInvoke(appName):
    startTime = utils.getTime()
    res = requests.post(url='http://<TODO>/bench/04/azure/%s' %appName)
    res = res.json()
    endTime = utils.getTime()
    return endTime - startTime

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
        chainLenSampleList = sampleGenerator.chainLenSampleListGen(SAMPLE_NUM)
        sampleGenerator.sampleActionGen(chainLenSampleList)
        print("Sample generation completes")
        print("-----------------------\n")
    resultFile = open(RESULT_FILENAME, "w")
    resultFile.write("appName,avgIAT,cv,latencies\n")
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
        resultFile.write("%s,%.2f,%.2f,%s\n" %(appName, result['avgIAT'], result['cv'], str(result['latencies'])[1:-1]))
    
    resultFile.close()
    testEndTime = utils.getTime()
    print("-----------------------")
    duration = (testEndTime - testStartTime) / MILLISECONDS_PER_SECOND
    print("Test duration: %.2f s" %duration)
    print("Test finished")

if __name__ == "__main__":
    generateInvokes()


def deploy():
    # cli 部署函数
    print(os.popen("tass-cli function create -c ./function/hello/code.zip -n bench-01-hello").read())
    # 部署各种 yaml 文件
    print(os.popen("kubectl apply -f ./function/hello/function.yaml -f ./workflow/hello/workflow.yaml").read())
    # 创建 Ingress 路由
    print(os.popen("tass-cli route create -n bench-01-hello -p /bench/01/hello").read())