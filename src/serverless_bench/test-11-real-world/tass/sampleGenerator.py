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

workflow_path = './workflow/azure/workflow.yaml'
function_path = './function/azure/function.yaml'

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
            'apiVersion': 'serverless.tass.io/v1alpha1',
            'kind': 'Workflow',
            'metadata': {
                'namespace': 'default',
                'name': workflow_name
            },
            'spec': {
                'env': {
                    'lang': 'CH',
                    'kind': 'pipeline'
                },
                'spec': []
            }
        }
        workflow_spec = {
            'name': 'flow',
            'statement': 'direct',
        }
        length = chainLenSampleList[sequenceID]
        for functionID in range(1, length + 1):
            func_name = 'bench-04-azure%d-%d' %sequenceID %functionID
            # Fill in workflow
            elem = workflow_spec.copy()
            elem['name'] += str(functionID)
            elem['function'] = func_name
            elem['output'] = ['flow'+str(functionID+1)]
            workflow['spec']['spec'].append(elem)
            # Create and apply functions
            function = {
                'apiVersion': 'serverless.tass.io/v1alpha1',
                'kind': 'Function',
                'metadata': {
                    'namespace': 'default',
                    'name': func_name
                },
                'spec': {
                    'environment': 'Golang',
                    'resource': {
                        'cpu': '1',
                        'memory': '128Mi'
                    }
                }
            }
            create_yaml_file(function, function_path)
            print(os.popen("tass-cli function create -c ./function/azure/code.zip -n " + func_name).read())
            print(os.popen("kubectl apply -f " + function_path).read())
        del workflow['spec']['spec'][-1]['output']
        if length == 1:
            elem['role'] = 'orphan'
        else:
            workflow['spec']['spec'][0]['role'] = 'start'
            workflow['spec']['spec'][-1]['role'] = 'end'
        # Apply workflow and create route
        create_yaml_file(workflow, workflow_path)
        print(os.popen("kubectl apply -f " + workflow_path).read())
        print(os.popen("tass-cli route create -p %s -n %s" %route_path %workflow_name).read())
        print("Sample creation complete")
    return 


if __name__ == '__main__':
    chainLenSampleList = chainLenSampleListGen(SAMPLE_NUM)
    sampleActionGen(chainLenSampleList)