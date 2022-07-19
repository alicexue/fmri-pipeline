"""
Functions for interacting with model_params, condition_key, and task_contrasts
"""

# Created by Alice Xue, 06/2018
from argparse import Namespace
import copy
import json
import numpy as np
import pandas as pd
import os
import sys

import directory_struct_utils

"""
Converts parameters in model_params.json to Namespace object 
"""


def model_params_json_to_namespace(studyid, basedir, modelname):
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    default_params = get_default_params()
    model_params_json_path = modeldir + '/model_params.json'
    if os.path.exists(model_params_json_path):
        try:
            params = json.load(open(model_params_json_path, 'r'))
        except ValueError:
            print("\nERROR: Could not read the %s file. Make sure it is formatted correctly." % model_params_json_path)
            sys.exit(-1)
        args = Namespace()
        args.modelname = params['modelname']
        args.specificruns = params['specificruns']
        args.studyid = params['studyid']
        args.basedir = params['basedir']
        args.anatimg = params['anatimg']
        args.hpf = not params['nohpf']
        args.use_inplane = params['use_inplane']
        args.whiten = not params['nowhiten']
        args.nonlinear = params['nonlinear']
        args.smoothing = params['smoothing']
        args.doreg = params['doreg']
        args.confound = not params['noconfound']  # args.confound instead of noconfound bc of dest
        args.spacetag = params['spacetag']
        if 'usebrainmask' in params:
            args.usebrainmask = params['usebrainmask']
        else:
            args.usebrainmask = default_params['usebrainmask']
        return args
    else:
        print("ERROR: model_params.json does not exist in %s" % modeldir)
        sys.exit(-1)


"""
Takes parameters from model_params.json and converts to string of commands
The list can be called on in a subprocess
"""


def model_params_json_to_list(studyid, basedir, modelname):
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    if os.path.exists(modeldir + '/model_params.json'):
        with open(modeldir + '/model_params.json', 'r') as f:
            params = json.load(f)

        # no_action_params: parameters that don't have store_true or store_false as an action
        no_action_params = ['studyid', 'basedir', 'smoothing', 'use_inplane', 'modelname', 'anatimg', 'spacetag']
        action_params = {'nonlinear': False, 'nohpf': True, 'nowhiten': True, 'noconfound': True, 'doreg': False,
                         'usebrainmask': False}
        # keys in action_params are arguments that have action that stores parameter as true/false
        # values in action_params are default arguments
        params_with_diff_dest = ['nohpf', 'nowhiten', 'noconfound']
        args = []
        for p in no_action_params:
            args.append('--' + p)
            args.append(str(params[p]))

        for p in action_params.keys():
            if p not in params:  # if parameter in action_params is not a parameter in model_params.json
                r_params = get_replacement_params()
                d_params = get_default_params()
                if r_params[p] is not None and r_params[p] in params:
                    # if p has been replaced with something else (like altBETmask has been replaced by usebrainmask),
                    # find the replacement in r_params (usebrainmask)
                    # take the original value of the parameter (altBETmask = True)
                    # then set the value of the new parameter to that value
                    print('WARNING: "%s" has been deprecated and replaced by "%s", see README for details' % (
                        r_params[p], p))
                    print('WARNING: %s has been set to the original value of %s: %s' % (
                        p, r_params[p], params[r_params[p]]))
                    params[p] = params[r_params[p]]
                else:
                    print('WARNING: "%s" has been deprecated and replaced by "%s"' % (r_params[p], p))
                    print("%s has been set to the default value: %s" % (r_params[p], d_params[p]))
                    params[p] = d_params[p]
            if p not in params_with_diff_dest:
                if params[p] != action_params[p]:
                    # if the passed parameter is not the same as the default value
                    args.append('--' + p)
            else:
                if params[p] == action_params[p]:
                    # if the passed parameter is same as the default value, then add this arg to do the opposite
                    args.append('--' + p)
        return args
    else:
        print("model_params.json does not exist in %s" % modeldir)
        sys.exit(-1)


"""
Creates subject and onset directories within level 1 model directory 
"""


def create_model_level1_dir(studyid, basedir, modelname):
    # Creates model dir, the subject dirs, onset dirs
    # no longer creates empty EV files - causes fsl errors if not removed by user
    studydir = os.path.join(basedir, studyid)
    study_info, hasSessions = directory_struct_utils.get_study_info(studydir)
    subs = sorted(study_info.keys())
    print(json.dumps(study_info))
    i = 0
    # iterate through the subjects, sessions, tasks, and runs
    for subid in subs:
        if hasSessions:
            sessions = sorted(study_info[subid].keys())
            for ses in sessions:
                tasks = sorted(study_info[subid][ses].keys())
                for task in tasks:
                    runs = study_info[subid][ses][task]
                    list.sort(runs)
                    for run in runs:
                        onsetsdir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname, subid,
                                                 ses, 'task-%s_run-%s' % (task, run), 'onsets')
                        if not os.path.exists(onsetsdir):
                            os.makedirs(onsetsdir)
                        i += 1
        else:
            tasks = sorted(study_info[subid].keys())
            for task in tasks:
                runs = study_info[subid][task]
                list.sort(runs)
                for run in runs:
                    onsetsdir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname, subid,
                                             'task-%s_run-%s' % (task, run), 'onsets')
                    if not os.path.exists(onsetsdir):
                        os.makedirs(onsetsdir)
                    i += 1
    print("Created %d onset directories" % i)
    return hasSessions


"""
Returns dictionary with parameters from model_params.json as keys and defaults values as values
Excludes studyid, basedir, specificruns, and modelname
"""


def get_default_params():
    default_params = {'smoothing': 0, 'use_inplane': 0, 'nonlinear': False, 'nohpf': True, 'nowhiten': True,
                      'noconfound': True, 'anatimg': '', 'doreg': False, 'spacetag': '', 'usebrainmask': False}
    return default_params


"""
Returns dictionary with replacements as keys and old parameters as values (or None if param isn't being replaced)
altBETmask is deprecated. Use usebrainmask instead 
"""


def get_replacement_params():
    new_params = {'usebrainmask': 'altBETmask'}
    return new_params


"""
Creates model_params.json if not found with default parameters
specificruns is set to all possible runs
"""


def create_level1_model_params_json(studyid, basedir, modelname):
    # Creates model_params.json file to define arguments
    # Keys must be spelled correctly

    studydir = os.path.join(basedir, studyid)
    study_info, hasSessions = directory_struct_utils.get_study_info(studydir)

    params = {'studyid': studyid, 'basedir': basedir, 'specificruns': study_info, 'modelname': modelname, }
    params.update(get_default_params())
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    if not os.path.exists(modeldir):
        os.makedirs(modeldir)

    if not os.path.exists(modeldir + '/model_params.json'):
        with open(modeldir + '/model_params.json', 'w') as outfile:
            json.dump(params, outfile, sort_keys=True, indent=4)
        print("Created sample model_params.json with default values")
    else:
        print("Found existing model_params.json")


"""
RunObj holds relevant information for a single run
sub: subject id (without prefix sub-)
ses: session name (without prefix ses-). Should be None if there are no sessions in the project
task: task name (without prefix task-)
run: run name (without prefix run-)
"""


class RunObj:
    def __init__(self, sub, ses, task, run):
        self.sub = sub
        self.ses = ses  # should be None if there are no sessions
        self.task = task
        self.run = run


"""
Returns list of RunObj for all runs in specificruns
Checks for existence of functional file before adding to the list
"""


def traverse_specificruns(studyid, basedir, specificruns, hasSessions):
    run_objects = []
    study_info = specificruns
    subs = sorted(study_info.keys())
    # iterate through each subject, session, task, and runs
    for subid in subs:
        sub = subid[len('sub-'):]  # sub is the subject ID without the prefix 'sub-'
        if hasSessions:
            sessions = sorted(study_info[subid].keys())
            for ses in sessions:
                sesname = ses[len('ses-'):]
                tasks = sorted(study_info[subid][ses].keys())
                for task in tasks:
                    runs = study_info[subid][ses][task]
                    list.sort(runs)
                    for run in runs:
                        funcdir = os.path.join(basedir, studyid, 'fmriprep', 'sub-' + sub, 'ses-' + sesname, 'func')
                        fileprefix = 'sub-' + sub + '_ses-' + sesname + '_task-' + task + '_run-' + run
                        funcdirfiles = os.listdir(funcdir)
                        if os.path.exists(funcdir):
                            for f in funcdirfiles:
                                if f.startswith(fileprefix):
                                    pass
                            run_objects.append(RunObj(sub, sesname, task, run))
        else:  # no sessions
            tasks = sorted(study_info[subid].keys())
            for task in tasks:
                runs = sorted(study_info[subid][task])
                for run in runs:
                    funcdir = os.path.join(basedir, studyid, 'fmriprep', 'sub-' + sub, 'func')
                    fileprefix = 'sub-' + sub + '_task-' + task + '_run-' + run
                    funcdirfiles = os.listdir(funcdir)
                    if os.path.exists(funcdir):
                        for f in funcdirfiles:
                            if f.startswith(fileprefix):
                                pass
                        run_objects.append(RunObj(sub, None, task, run))
    return run_objects


"""
Return list of confounds filepaths to search for
"""


def get_possible_confounds_stems():
    return [
        '_bold_confounds.tsv',
        '_desc-confounds_regressors.tsv',
        '_desc-confounds_timeseries.tsv'
    ]


"""
Gets list of all possible confounds from a *_bold_confounds.tsv file in fmriprep
(by iterating through fmriprep until a confounds file is found)
Returns column names of *_bold_confounds.tsv, the list of all possible confounds
Returns an empty list if no *_bold_confounds.tsv file is found
"""


def get_possible_confounds(studyid, basedir):
    studydir = os.path.join(basedir, studyid)
    study_info, hasSessions = directory_struct_utils.get_study_info(studydir)
    run_objects = traverse_specificruns(studyid, basedir, study_info, hasSessions)
    run_objects_count = 0
    found_bold_confounds = False
    while run_objects_count < len(run_objects) and not found_bold_confounds:
        # iterates through all runs in fmriprep to look for bold_confounds
        spef_run = run_objects[run_objects_count]  # checks one run in list
        if spef_run.ses is not None:  # there are sessions
            funcdir = os.path.join(basedir, studyid, 'fmriprep', 'sub-' + spef_run.sub, 'ses-' + spef_run.ses, 'func')
            fileprefix = 'sub-' + spef_run.sub + '_ses-' + spef_run.ses + '_task-' + spef_run.task + '_run-' + \
                         spef_run.run
        else:  # no sessions
            funcdir = os.path.join(basedir, studyid, 'fmriprep', 'sub-' + spef_run.sub, 'func')
            fileprefix = 'sub-' + spef_run.sub + '_task-' + spef_run.task + '_run-' + spef_run.run

        possible_confounds_filepath_stems = get_possible_confounds_stems()

        for stem in possible_confounds_filepath_stems:
            confounds_filepath = os.path.join(funcdir, fileprefix + stem)
            try:
                df = pd.read_csv(confounds_filepath, delim_whitespace=True)
                possible_confounds = df.columns.tolist()
                return possible_confounds
            except FileNotFoundError:
                continue
        run_objects_count += 1
    print('Could not find confounds files in %s. Looked for files ending with the following strings:' % funcdir,
          possible_confounds_filepath_stems)
    return []


"""
Asks if user wants to create a confounds.json file and whether or not to overwrite
Default confounds.json file {"confounds":[<list of all possible confounds>]}
"""


def create_default_confounds_json(studyid, basedir, modelname):
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    possible_confounds = get_possible_confounds(studyid, basedir)
    confounds_dict = {'confounds': possible_confounds}
    overwrite = False
    if os.path.exists(modeldir + '/confounds.json'):
        rsp = None
        while rsp != '' and rsp != 'n':
            rsp = input(
                'Do you want to overwrite the existing confounds.json file with all possible confounds? (ENTER/n) ')
        if rsp == '':
            overwrite = True
        else:
            overwrite = False
    if overwrite or not os.path.exists(modeldir + '/confounds.json'):
        with open(modeldir + '/confounds.json', 'w') as outfile:
            json.dump(confounds_dict, outfile, indent=4)
        print(
            'Created confounds.json with list of all possible confounds from *_bold_confounds.tsv. File is located '
            'here: %s' % (
                    modeldir + '/confounds.json'))
        print('Make sure to modify this file before running level 1 analysis')
    else:
        print('Did not overwrite existing confounds file found here: %s' % (modeldir + '/confounds.json'))


"""
Auto-generates confounds files in onset directories based on list of confounds in confounds.json
"""


def generate_confounds_files(studyid, basedir, specificruns, modelname, hasSessions):
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    if os.path.exists(modeldir + '/confounds.json'):
        with open(modeldir + '/confounds.json', 'r') as f:
            confounds_dict = json.load(f)
            confounds_list = confounds_dict['confounds']
        run_objects = traverse_specificruns(studyid, basedir, specificruns, hasSessions)
        runs_without_bold_confounds = []
        for spef_run in run_objects:
            if spef_run.ses is not None:  # there are sessions
                funcdir = os.path.join(basedir, studyid, 'fmriprep', 'sub-' + spef_run.sub, 'ses-' + spef_run.ses,
                                       'func')
                fileprefix = 'sub-' + spef_run.sub + '_ses-' + spef_run.ses + '_task-' + spef_run.task + '_run-' + \
                             spef_run.run
                modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-' + modelname,
                                        'sub-' + spef_run.sub, 'ses-' + spef_run.ses,
                                        'task-' + spef_run.task + '_run-' + spef_run.run, 'onsets')
            else:  # no sessions
                funcdir = os.path.join(basedir, studyid, 'fmriprep', 'sub-' + spef_run.sub, 'func')
                fileprefix = 'sub-' + spef_run.sub + '_task-' + spef_run.task + '_run-' + spef_run.run
                modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-' + modelname,
                                        'sub-' + spef_run.sub, 'task-' + spef_run.task + '_run-' + spef_run.run,
                                        'onsets')

            possible_confounds_filepath_stems = get_possible_confounds_stems()

            foundConfounds = False
            for stem in possible_confounds_filepath_stems:
                potential_confounds_filepath = os.path.join(funcdir, fileprefix + stem)
                try:
                    df = pd.read_csv(potential_confounds_filepath, delim_whitespace=True)
                    foundConfounds = True
                    confounds_filepath = potential_confounds_filepath
                except FileNotFoundError:
                    continue

            if foundConfounds:
                confounds_tsv = pd.read_csv(confounds_filepath, delim_whitespace=True)
                cf = confounds_tsv.reindex(columns=confounds_list)
                # replace np values with 0's
                cf = cf.replace({np.nan: 0})
                output_confounds_filename = fileprefix + '_ev-confounds.tsv'
                cf.to_csv(os.path.join(modeldir, output_confounds_filename), sep='\t', header=0, index=False)
                print('Created confounds file for %s' % fileprefix)
            else:
                # keep track of all runs for which *_bold_confounds.tsv files can't be found
                runs_without_bold_confounds.append(spef_run)

        # print warning message for runs without confounds
        if len(runs_without_bold_confounds) > 0:
            print('WARNING: confounds files were not found for the following runs:')
            for spef_run in runs_without_bold_confounds:
                if spef_run.ses is not None:
                    print(
                        '\t' + 'sub-' + spef_run.sub + '_ses-' + spef_run.ses + '_task-' + spef_run.task + '_run-' +
                        spef_run.run)
                else:
                    print('\t' + 'sub-' + spef_run.sub + '_task-' + spef_run.task + '_run-' + spef_run.run)


"""
Creates empty condition_key.json if not found
"""


def create_empty_condition_key(studyid, basedir, modelname):
    # Creates an empty sample condition key
    # Gets the name of all possible tasks (that the first subject did), and adds those to the condition key
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    if not os.path.exists(modeldir):
        os.makedirs(modeldir)

    studydir = os.path.join(basedir, studyid)
    study_info, hasSessions = directory_struct_utils.get_study_info(studydir)
    all_tasks = []
    subs = sorted(study_info.keys())
    subid = subs[0]
    if hasSessions:
        sessions = sorted(study_info[subid].keys())
        for ses in sessions:
            tasks = sorted(study_info[subid][ses].keys())
            all_tasks = tasks
    else:
        tasks = sorted(study_info[subid].keys())
        all_tasks = tasks

    if not os.path.exists(modeldir + '/condition_key.json'):
        with open(modeldir + '/condition_key.json', 'w') as outfile:
            condition_key = {}
            for task in all_tasks:
                condition_key[task] = {"1": ""}
            json.dump(condition_key, outfile, sort_keys=True, indent=4)
        print("Created empty condition_key.json")
    else:
        print("Found existing condition_key.json")


"""
Creates empty task_contrasts.json if not found
"""


def create_empty_task_contrasts_file(studyid, basedir, modelname):
    # Creates an empty task_contrasts file with the task names as keys
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    if not os.path.exists(modeldir):
        os.makedirs(modeldir)

    studydir = os.path.join(basedir, studyid)
    study_info, hasSessions = directory_struct_utils.get_study_info(studydir)
    all_tasks = []
    subs = sorted(study_info.keys())
    subid = subs[0]
    if hasSessions:
        sessions = sorted(study_info[subid].keys())
        for ses in sessions:
            tasks = sorted(study_info[subid][ses].keys())
            all_tasks = tasks
    else:
        tasks = sorted(study_info[subid].keys())
        all_tasks = tasks

    if not os.path.exists(modeldir + '/task_contrasts.json'):
        with open(modeldir + '/task_contrasts.json', 'w') as outfile:
            condition_key = {}
            for task in all_tasks:
                condition_key[task] = {"1": [0, 0, 0]}
            json.dump(condition_key, outfile, sort_keys=True, indent=4)
        print("Created empty task_contrasts.json")
    else:
        print("Found existing task_contrasts.json")


"""
Modifies model_param.json based on user input
"""


def check_model_params_cli(studyid, basedir, modelname):
    # Modifies model_params by interacting with user through the command line
    modeldir = os.path.join(basedir, studyid, 'model', 'level1', 'model-%s' % modelname)
    new_params = {}
    if os.path.exists(modeldir + '/model_params.json'):
        with open(modeldir + '/model_params.json', 'r') as f:
            params = json.load(f)
            new_params['modelname'] = params['modelname']
            # not including modelname
            ordered_params = ['studyid', 'basedir', 'specificruns', 'anatimg', 'nohpf', 'use_inplane', 'nowhiten',
                              'nonlinear', 'smoothing', 'doreg', 'noconfound', 'spacetag', 'usebrainmask']

            for param in ordered_params:
                if param not in params:  # param from ordered_params isn't in model_param.json
                    default_params = get_default_params()
                    cur_val = default_params[param]
                else:
                    cur_val = params[param]
                if isinstance(cur_val, dict):
                    pprint_val = json.dumps(cur_val)
                else:
                    pprint_val = cur_val
                if isinstance(cur_val, str) and len(cur_val) == 0:
                    pprint_val = '\"\"'
                print('\n', param + ':', pprint_val)
                rsp = None
                while rsp != 'y' and rsp != '':
                    rsp = input('Do you want to change %s? (y/ENTER) ' % param)
                if rsp == 'y':
                    if isinstance(cur_val, bool):  # if it's a boolean, just reverse it
                        new_params[param] = not cur_val
                    else:
                        if param == 'specificruns':  # this is a dictionary/json object
                            new_params[param] = input_to_modify_specificruns(studyid, basedir, params[param])
                        else:
                            validinput = False
                            while not validinput:
                                new_param_val = input('New value of %s: ' % param)
                                if isinstance(cur_val, int):
                                    try:  # make sure input is integer
                                        new_param_val = int(new_param_val)
                                        new_params[param] = new_param_val
                                        validinput = True
                                    except ValueError:
                                        validinput = False
                                else:
                                    new_params[param] = new_param_val
                                    validinput = True

                    if isinstance(cur_val, dict):
                        print('%s changed to %s' % (param, json.dumps(new_params[param])))
                    else:
                        pprint_val = new_params[param]
                        if isinstance(pprint_val, str) and len(pprint_val) == 0:
                            pprint_val = '\"\"'
                        print('%s changed to %s' % (param, pprint_val))
                else:
                    new_params[param] = cur_val
    with open(modeldir + '/model_params.json', 'w') as outfile:
        json.dump(new_params, outfile, sort_keys=True, indent=4)
        print('\nUpdated %s.' % (modeldir + '/model_params.json'))
        for param in ['modelname'] + ordered_params:
            if isinstance(new_params[param], dict):
                pprint_val = json.dumps(new_params[param])
            else:
                pprint_val = new_params[param]
            if isinstance(pprint_val, str) and len(pprint_val) == 0:
                pprint_val = '\"\"'
            print(param + ':', pprint_val)


"""
Modifies specificruns based on user input 
Prints instructions for modifying specificruns
If parameter specificruns is empty, will retrieve all runs and set specificruns to that
"""


def input_to_modify_specificruns(studyid, basedir, specificruns):
    if len(specificruns) == 0:
        studydir = os.path.join(basedir, studyid)
        study_info, hasSessions = directory_struct_utils.get_study_info(studydir)
        print('Here are all of the runs in %s:' % (os.path.join(basedir, studyid, 'fmriprep')))
        print('\n', json.dumps(study_info), '\n')

        specificruns = study_info

    print('Four entities exist in the BIDS specification: subject (sub-), session (ses-), task (task-), and run (run-)')
    print(
        'To exclude all instances of a sub|ses|task|run, enter the full name of the sub|ses|task|run to exclude ('
        'including the tag in the beginning)')
    print('\t(e.g. sub-01)')
    print('To exclude a specific ses|task|run, enter each entity separated by forward slashes.')
    print('The entities must be in descending order, where sub > ses > task > run')
    print('\t(e.g. sub-01/ses-01/task-flanker/run-2 (to exclude this specific run))')
    print('\t(e.g. sub-02/ses-01/task-flanker (to exclude this specific task for this subject))')
    print(
        'Use commas to separate multiple exclusion criteria or enter each criteria one by one and press ENTER when '
        'you are finished modifying specificruns')
    print('\t(e.g. sub-02,sub-01/ses-01/task-flanker)')
    print('Note: In the specificruns object, the tags task- and run- are omitted for better readability.')

    continueAsking = True
    while continueAsking:
        items_to_exclude = input('Exclude the following: ')
        if items_to_exclude == '':
            continueAsking = False
        else:
            items_to_exclude_list = items_to_exclude.split(',')
            for i in range(0, len(items_to_exclude_list)):
                items_to_exclude_list[i] = items_to_exclude_list[i].strip()  # remove any trailing/leading whitespace
            for item in items_to_exclude_list:
                if '/' in item:
                    specificruns = remove_specific_items_from_study_info(item, specificruns)
                else:
                    specificruns = remove_from_study_info(item, specificruns)
        print('New specificruns: ', json.dumps(specificruns))
    return specificruns


"""
item: string that starts with "sub-", "ses-", "task-", or "run-"
"""


def remove_from_study_info(item, specificruns):
    try:
        assert list(specificruns.values()[0].keys())[0].startswith('ses-')
        hasSessions = True
    except AssertionError:
        hasSessions = False
    if item.startswith("sub-") or item.startswith("ses-") or item.startswith("task-") or item.startswith("run-"):
        study_info = specificruns
        study_info_copy = copy.deepcopy(study_info)
        subs = sorted(study_info.keys())
        if item.startswith('sub-') and item in subs:
            del study_info_copy[item]
        # iterate through each subject, session, task, and runs
        for subid in subs:
            if hasSessions:
                sessions = sorted(study_info[subid].keys())
                if item.startswith('ses-') and item in sessions:
                    del study_info_copy[subid][item]
                    if len(study_info_copy[subid]) == 0:
                        del study_info_copy[subid]
                for ses in sessions:
                    tasks = sorted(study_info[subid][ses].keys())
                    if item.startswith('task-') and item[len('task-'):] in tasks:
                        del study_info_copy[subid][ses][item[len('task-'):]]
                        if len(study_info_copy[subid][ses]) == 0:
                            del study_info_copy[subid][ses]
                    for task in tasks:
                        runs = study_info[subid][ses][task]
                        if item.startswith('run-') and item[len('run-'):] in runs:
                            study_info_copy[subid][ses][task].remove(item[len('run-'):])
                            if len(study_info_copy[subid][ses][task]) == 0:
                                del study_info_copy[subid][ses][task]
            else:  # no sessions
                tasks = sorted(study_info[subid].keys())
                if item.startswith('task-') and item[len('task-'):] in tasks:
                    del study_info_copy[subid][item[len('task-'):]]
                    if len(study_info_copy[subid]) == 0:
                        del study_info_copy[subid]
                for task in tasks:
                    runs = study_info[subid][task]
                    if item.startswith('run-') and item[len('run-'):] in runs:
                        study_info_copy[subid][task].remove(item[len('run-'):])
                        if len(study_info_copy[subid][task]) == 0:
                            del study_info_copy[subid][task]

        return study_info_copy
    else:
        print('ERROR: Invalid item to remove. Must start with "sub-", "ses-", "task-", or "run-"')
        return specificruns


"""
items:  string with sub/ses/task/run separated by forward slashes. 
        Each item starts with the appropriate tag ("sub-","ses-",...)
specificruns: nested dictionary that details each sub, ses, task, run
"""


def remove_specific_items_from_study_info(items, study_info):
    specificruns = copy.deepcopy(study_info)
    item_values = {'sub-': 0, 'ses-': 1, 'task-': 2, 'run-': 3}
    curr_value = -1
    item_list = items.split('/')
    parsed_item_list = []
    valid = True
    correctOrder = True
    for item in item_list:
        if item.startswith("sub-") or item.startswith("ses-") or item.startswith("task-") or item.startswith("run-"):
            head_tag = item[:item.find('-') + 1]
            if head_tag in item_values:
                if item_values[head_tag] > curr_value:
                    curr_value = item_values[head_tag]
                    if item.startswith("task-"):
                        parsed_item_list.append(item[len('task-'):])
                    elif item.startswith("run-"):
                        parsed_item_list.append(item[len('run-'):])
                    else:
                        parsed_item_list.append(item)
                else:
                    correctOrder = False
        else:
            if item != '':  # if there's an empty value
                valid = False
    if correctOrder and valid:
        if check_for_item_in_study_info(specificruns, parsed_item_list, 0):
            return delete_specific_item_in_study_info(specificruns, parsed_item_list, 0)
        else:
            print('ERROR: Specified items not found.')
    if not valid:
        print('ERROR: Invalid format.')
    if not correctOrder:
        print('ERROR: Incorrect order')
    return specificruns


"""
Recursive function that deletes a ses/task/run specified by item_list from the nested dictionary specificruns
specificruns: nested dictionary that details each sub, ses, task, run
item_list: list of nested keys that should be in specificruns
items_index: int that keeps track of current item in item_list that is being searched
Returns specificruns with the item in item_list removed
"""


def delete_specific_item_in_study_info(specificruns, item_list, items_index):
    if items_index < len(item_list) - 1:
        item = item_list[items_index]
        if item in specificruns.keys():
            new_items = delete_specific_item_in_study_info(specificruns[item], item_list,
                                                           items_index + 1)  # iterate through recursive dictionary
            if len(new_items) > 0:
                specificruns[item] = new_items
            else:
                del specificruns[item]
            return specificruns
    elif items_index == len(item_list) - 1:  # reached last item in item_list, which should be removed
        item = item_list[items_index]
        if isinstance(specificruns, dict):
            if item in specificruns.keys():
                del specificruns[item]
                return specificruns
        elif isinstance(specificruns, list):  # runs are a list, not dictionary
            if item in specificruns:
                specificruns.remove(item)
                return specificruns
    return specificruns


"""
Recursive function that looks for each item in item_list in the nested dictionary specificruns
specificruns: nested dictionary that details each sub, ses, task, run
item_list: list of nested keys that should be in specificruns
items_index: int that keeps track of current item in item_list that is being searched
Returns True if item_list is a list of nested keys in specificruns
"""


def check_for_item_in_study_info(specificruns, item_list, items_index):
    if items_index < len(item_list) - 1:
        item = item_list[items_index]
        if item in specificruns.keys():
            return check_for_item_in_study_info(specificruns[item], item_list, items_index + 1)
    elif items_index == len(item_list) - 1:  # reached last item in item_list
        item = item_list[items_index]
        if isinstance(specificruns, dict):
            if item in specificruns.keys():
                return True
        elif isinstance(specificruns, list):  # runs are a list, not dictionary
            if item in specificruns:
                return True
    return False
