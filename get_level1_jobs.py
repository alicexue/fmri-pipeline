"""
Gets a list of level 1 feats to create (excludes feats that already exist)
The list of jobs is used by run_level1.py and passed to run_feat_job.py as a dictionary
run_feat_job.py calls mk_level1_fsf_bbr.py
"""

# Created by Alice Xue, 06/2018

import argparse
import copy
import json
import os

import directory_struct_utils
import setup_utils


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='get_jobs')

    parser.add_argument('--studyid', dest='studyid',
                        required=True, help='Study ID')
    parser.add_argument('--basedir', dest='basedir',
                        required=True, help='Base directory (above studyid directory)')
    parser.add_argument('-m', '--modelname', dest='modelname',
                        required=True, help='Model name')
    parser.add_argument('--nofeat', dest='nofeat', action='store_true',
                        default=False, help='Only create the fsf\'s, don\'t call feat')
    parser.add_argument('-s', '--specificruns', dest='specificruns', type=json.loads,
                        default={}, help="""JSON object in a string that details which runs to create fsf's for. If 
                        specified, ignores specificruns specified in model_params.json. Ex: If there are sessions: 
                        \'{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", 
                        "2"]}}}\' where flanker is a task name and ["1", "2"] is a list of the runs. If there aren't 
                        sessions: \'{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}\'. Make sure this 
                        describes the fmriprep folder, which should be in BIDS format. Make sure to have single 
                        quotes around the JSON object and double quotes within. """
                        )
    args = parser.parse_args(argv)
    return args


def add_args(args, sub, task, run, nofeat):
    args.append('--sub')
    args.append(sub)
    args.append('--taskname')
    args.append(task)
    args.append('--runname')
    args.append(run)
    if not nofeat:
        args.append('--callfeat')
    return args


def main(argv=None):
    sys_args = parse_command_line(argv)
    print(json.dumps(sys_args))

    studyid = sys_args.studyid
    basedir = sys_args.basedir
    modelname = sys_args.modelname
    specificruns = sys_args.specificruns
    nofeat = sys_args.nofeat

    args = setup_utils.model_params_json_to_namespace(studyid, basedir, modelname)
    print(json.dumps(args))

    if specificruns == {}:  # if specificruns from sys.argv is empty (default), use specificruns from model_param
        specificruns = args.specificruns
    get_level1_jobs(studyid, basedir, modelname, specificruns, sys_args.specificruns, nofeat)


def get_level1_jobs(studyid, basedir, modelname, specificruns, sys_args_specificruns, nofeat):
    """
    Args:
        studyid: name of the parent directory of the fmriprep directory
        basedir: full path of the grandparent directory of the fmriprep directory
        modelname: name of model
        specificruns (dict): from model_params.json
        sys_args_specificruns (dict): passed into the program through the command line (sys.args)
        nofeat: boolean; don't run Feat if True, run Feat if False
    """
    # gets parameters set in model_param.json
    setup_utils.model_params_json_to_namespace(studyid, basedir, modelname)

    # gets dictionary of study information
    study_info = specificruns
    hasSessions = False
    if specificruns == {}:  # if specificruns in model_params was empty
        studydir = os.path.join(basedir, studyid)
        study_info, hasSessions = directory_struct_utils.get_study_info(studydir)
    else:
        l1 = list(study_info.keys())
        l2 = list(study_info[l1[0]].keys())[0]
        if l2.startswith('ses-'):
            hasSessions = True
    print(json.dumps(study_info))

    # convert model params into a list of arguments that can be used to call mk_level1_fsf_bbr
    # contains all the model params but not specific info like subject, task, run
    sys_argv = setup_utils.model_params_json_to_list(studyid, basedir, modelname)

    # created a deep copy of study_info (want to remove runs from the copy and not the original)
    study_info_copy = copy.deepcopy(study_info)

    existing_feat_files = []
    jobs = []  # list of list of arguments to run mk_level1_fsf_bbr on
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
                        # check if feat exists for this run
                        model_subdir = '%s/model/level1/model-%s/%s/%s/task-%s_run-%s' % (
                            os.path.join(basedir, studyid), modelname, subid, ses, task, run)
                        feat_file = "%s/%s_%s_task-%s_run-%s.feat" % (model_subdir, subid, ses, task, run)
                        if sys_args_specificruns == {} and os.path.exists(
                                feat_file):
                            # if subject didn't pass in specificruns and a feat file for this run exists
                            existing_feat_files.append(feat_file)
                            print("WARNING: Existing feat file found: %s" % feat_file)
                            runs_copy = study_info_copy[subid][ses][task]
                            runs_copy.remove(run)  # removes the run since a feat file for it already exists
                        else:  # if subject passed in specificruns
                            if os.path.exists(feat_file):
                                existing_feat_files.append(feat_file)
                                print("WARNING: Existing feat file found: %s" % feat_file)
                            args = sys_argv[:]  # copies over the list of model params
                            args = add_args(args, sub, task, run, nofeat)  # adds subject, task, and run
                            args.append('--ses')  # adds session
                            args.append(sesname)
                            jobs.append(args)  # each list 'args' specifies the arguments to run mk_level1_fsf_bbr on
                    if len(study_info_copy[subid][ses][task]) == 0:  # if there are no runs for this task
                        del study_info_copy[subid][ses][task]  # remove the task from the dictionary
                    if len(study_info_copy[subid][ses]) == 0:  # if there are no tasks for this session
                        del study_info_copy[subid][ses]  # remove the ses from dictionary
        else:  # no sessions
            tasks = sorted(study_info[subid].keys())
            for task in tasks:
                runs = study_info[subid][task]
                list.sort(runs)
                for run in runs:
                    # check if feat exists for this run
                    model_subdir = '%s/model/level1/model-%s/%s/task-%s_run-%s' % (
                        os.path.join(basedir, studyid), modelname, subid, task, run)
                    feat_file = "%s/%s_task-%s_run-%s.feat" % (model_subdir, subid, task, run)
                    if sys_args_specificruns == {} and os.path.exists(
                            feat_file):  # if subject didn't pass in specificruns and a feat file for this run exists
                        existing_feat_files.append(feat_file)
                        print("WARNING: Existing feat file found: %s" % feat_file)
                        runs_copy = study_info_copy[subid][task]
                        runs_copy.remove(run)  # removes the run since a feat file for it already exists
                    else:  # if subject passed in specificruns
                        if os.path.exists(feat_file):
                            existing_feat_files.append(feat_file)
                            print("WARNING: Existing feat file found: %s" % feat_file)
                        args = sys_argv[:]
                        args = add_args(args, sub, task, run, nofeat)
                        jobs.append(args)
                if len(study_info_copy[subid][task]) == 0:  # if there are no runs for this task
                    del study_info_copy[subid][task]  # remove the task from the dictionary
        if len(study_info_copy[subid]) == 0:  # if there are no sessions or tasks for this subject left
            del study_info_copy[subid]

    additional_existing_feat_files = []
    # get additional existing feat files - any with + characters in their name
    for feat_file in existing_feat_files:
        upper_feat_dir = os.path.dirname(feat_file)
        dircontents = os.listdir(upper_feat_dir)
        for f in dircontents:
            if os.path.join(upper_feat_dir, f) not in existing_feat_files and len(os.path.split(f)) > 0 and \
                    os.path.split(f)[-1]:  # get file NAME without path
                filename = os.path.split(f)[-1]
                if filename.endswith('.feat'):
                    additional_existing_feat_files.append(os.path.join(upper_feat_dir, f))
                    print("WARNING: Existing feat file found: %s" % (os.path.join(upper_feat_dir, f)))

    existing_feat_files = existing_feat_files + additional_existing_feat_files

    if len(study_info_copy.keys()) == 0:
        print("WARNING: All runs for all subjects have been run on this model. Remove the feat files if you want to "
              "rerun them.")
        return existing_feat_files, jobs
    elif sys_args_specificruns == {} and len(existing_feat_files) != 0:
        # if the user didn't pass in specificruns and existing feat files were found
        print("WARNING: Some subjects' runs have already been run on this model. If you want to rerun these subjects, "
              "remove their feat directories first. To run the remaining subjects, rerun run_level1.py and add:")
        print("-s \'%s\'" % (json.dumps(study_info_copy)))
        return existing_feat_files, jobs
    else:  # no existing feat files were found
        print(len(jobs), "jobs")
        return existing_feat_files, jobs


if __name__ == '__main__':
    main()
