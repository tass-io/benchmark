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

import random
import os
import yaml

config = yaml.load(open(os.path.join(os.path.dirname(__file__),'config.yaml')), yaml.FullLoader)
SAMPLE_NUM = config['sample_number']

workflow_path = './workflow.wf.yaml'

def create_yaml_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    yaml.dump(object, file)
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
    sampleNum = len(chainLenSampleList)
    for sequenceID in range(sampleNum):
        route_path = "/bench/04/azure/%d" %sequenceID
        workflow_name = 'bench-04-azure%d' %sequenceID
        # Create workflow
        workflow = {
            'apiVersion': 1,
            'tasks': {},
        }
        task = {
            'run': 'bench-02-chained',
        }
        length = chainLenSampleList[sequenceID]
        for functionID in range(1, length + 1):
            func_name = 'bench-04-azure%d-%d' %sequenceID %functionID
            # Fill in workflow
            elem = task.copy()
            elem["run"] = func_name
            if functionID > 1:
                elem['inputs'] = {
                    'body': "{ output('Flow%d') }" %(functionID-1) 
                }
                elem['requires'] = ["Flow%d" %(functionID-1)]
            workflow['tasks']['Flow%d' %functionID] = elem
            # Create and apply functions
            print(os.popen("fission fn create --name %s --env go --src code.zip --entrypoint Handler --maxmemory 128" %func_name).read())
        workflow['output'] = "Flow%d" %length
        # Create workflow and apply it
        create_yaml_file(workflow, workflow_path)
        print(os.popen("fission fn create --name bench-04-azurewf%d --env go --src %s" %sequenceID %workflow_path).read())
        print(os.popen("fission httptrigger create --method POST --url \"%s\" --function bench-04-azurewf%d" %route_path %sequenceID).read())
        print("Sample creation complete")
    return 


if __name__ == '__main__':
    chainLenSampleList = chainLenSampleListGen(SAMPLE_NUM)
    sampleActionGen(chainLenSampleList)