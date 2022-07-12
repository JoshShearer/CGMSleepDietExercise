import yaml

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

    # for key in experience_level.keys():
    #     if experience_level[key]:
    #         at_least_one_experience = True
    # assert at_least_one_experience
    #
    # assert len(parameters['jobTypes']) > 0
    # job_types = parameters.get('jobTypes', [])
    # at_least_one_job_type = False
    # for key in job_types.keys():
    #     if job_types[key]:
    #         at_least_one_job_type = True
    # assert at_least_one_job_type
    #
    # assert len(parameters['date']) > 0
    # date = parameters.get('date', [])
    # at_least_one_date = False
    # for key in date.keys():
    #     if date[key]:
    #         at_least_one_date = True
    # assert at_least_one_date
    #
    # assert len(parameters['positions']) > 0
    # assert len(parameters['locations']) > 0
    #
    # assert len(parameters['uploads']) >= 1 and 'resume' in parameters['uploads']


    return parameters


if __name__ == '__main__':

    parameters = validate_yaml()

    instance = CGMProcessing(parameters)

    instance.capture_data()

