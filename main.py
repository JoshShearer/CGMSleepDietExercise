import yaml
import os

from cgmprocessing import CGMProcessing

def validate_yaml():
    with open("config.yaml", 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    mandatory_params = ['dataFiles', 'dateRange', 'outputFileDirectory']

    for mandatory_param in mandatory_params:
        if mandatory_param not in parameters:
            raise Exception(mandatory_param + ' is not inside the yml file!')

    assert len(parameters['dataFiles']) > 1
    assert len(parameters['dateRange']) == 2
    fileData = parameters.get('dataFiles', [])
    assert 'CGMData' in fileData
    assert 'mealData' in fileData
    
    assert os.path.isdir(parameters['outputFileDirectory']), "output directory does not exist"

    return parameters


if __name__ == '__main__':

    parameters = validate_yaml()

    instance = CGMProcessing(parameters)

    instance.capture_data()
    instance.clean_data()
    instance.process_mealData()
    instance.deep_analysis()

