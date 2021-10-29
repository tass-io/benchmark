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

import random, time, subprocess
import os, json
import yaml

name = "bench-04-azure"

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_role = "arn:aws-cn:iam::648513213171:role/sail-step-functions"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
machine_path = './stepfunctions'

def wait():
    time.sleep(6)

def cmd(cmd):
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    print(res)
    return res

def empty_str(str):
    return len(str) == 0
    
def clear_all():
    while not empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s" %name)):
        cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws lambda --profile linxuyalun delete-function --function-name {}" %name)
        wait()
    while not empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s" %name)):
        cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws stepfunctions delete-state-machine --profile linxuyalun --state-machine-arn %s{}" %(name, stepfuncs_arn))
        wait()

config = yaml.load(open(os.path.join(os.path.dirname(__file__),'config.yaml')), yaml.FullLoader)
SAMPLE_NUM = config['sample_number']

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

# Generate a list of length according to the CDF of the chain length in an app, 
# each of which represents the chain length of an application 
def chainLenSampleListGen(sampleNum):
    CDF = parseChainLenCDFFile()
    lengthList = CDF[0]
    CDFdict = CDF[1]
    
    sampleList = []
    for i in range(sampleNum):
        randF = random.random()
        for length in lengthList:
            if CDFdict[length] > randF:
                sampleList.append(length)
                break
    return sampleList

# parse the CDF file, return the list of each x (x is length in the CDF), 
# and the dictionary of x:F(x) 
def parseChainLenCDFFile():
    filename = os.path.join(os.path.dirname(__file__),'CDFs','chainlenCDF.csv')
    f = open(filename, 'r')
    f.readline()
    lengthList = []
    CDFdict = {}
    for line in f:
        lineSplit = line.split(',')
        length = int(lineSplit[0])
        Fx = float(lineSplit[1])
        lengthList.append(length)
        CDFdict[length] = Fx

    return (lengthList, CDFdict)

# Generate the script to create the samples on OpenWhisk
def sampleActionGen(chainLenSampleList):
    clear_all()
    sampleNum = len(chainLenSampleList)
    for sequenceID in range(sampleNum):
        # Create machine
        machine = {
            "Comment": "Tass ServerlessBench test 4 - real world azure",
            "StartAt": "%s1" %name,
            "TimeoutSeconds": 300, # maximum is 5 min
            "States": {}
        }
        state = {
            "Type": "Task"
        }
        length = chainLenSampleList[sequenceID]
        for functionID in range(1, length + 1):
            elem = state.copy()
            elem['Resource'] = "%s%s%d-%d" %(func_arn, name, sequenceID, functionID)
            if functionID != length:
                elem['Next'] = "%s%d" %(name, functionID+1)
            else:
                elem['End'] = True
            machine['States']['%s%d' %(name, functionID)] = elem
            # Create and apply functions
            cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 512 --timeout 900 --role %s --zip-file fileb://code.zip --function-name %s%d-%d" %(func_role, name, sequenceID, functionID))
            # wait until function created:
            while empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s%d-%d" %(name, sequenceID, functionID))):
                wait()
        # Create stepfunction machine and apply it
        create_json_file(machine, machine_path)
        cmd("aws stepfunctions create-state-machine --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s%d" %(stepfuncs_role, name, sequenceID))
        # wait until machine created:
        while empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep %s%d" %(name,sequenceID))):
            wait()
        print("Sample %d creation complete" %sequenceID)
    return 


if __name__ == '__main__':
    clear_all()
    chainLenSampleList = chainLenSampleListGen(SAMPLE_NUM)
    sampleActionGen(chainLenSampleList)