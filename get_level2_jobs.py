"""
Get information to run mk_level2_fsf on multiple subjects, tasks, runs, etc
Called by run_level2_feat.py
"""

# Created by Alice Xue, 06/2018

import argparse
import copy
import json
import os
import sys

import setup_utils


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='get_jobs')

    parser.add_argument('--studyid', dest='studyid',
                        required=True, help='Study ID')
    parser.add_argument('--basedir', dest='basedir',
                        required=True, help='Base directory (above studyid directory)')
    parser.add_argument('--nofeat', dest='nofeat', action='store_true',
                        default=False, help='Only create the fsf\'s, don\'t call feat')
    parser.add_argument('-s', '--specificruns', dest='specificruns', type=json.loads,
                        default={}, help="""JSON object in a string that details which runs to create fsf's for. Ex: 
                        If there are sessions: \'{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": 
                        {"flanker": ["1", "2"]}}}\' where flanker is a task name and ["1", "2"] is a list of the 
                        runs. If there aren't sessions: \'{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1",
                        "2"]}}\'. Make sure this describes the fmriprep folder, which should be in BIDS format. Make 
                        sure to have single quotes around the JSON object and double quotes within. """
                        )
    parser.add_argument('-m', '--modelname', dest='modelname',
                        required=True, help='Model name')
    parser.add_argument('--sessions', dest='sessions', nargs='+',
                        default=[], help='Name of session (not including prefix "sub-"')

    args = parser.parse_args(argv)
    return args


def add_args(args, sub, task, runs, nofeat):
    args.append('--sub')
    args.append(sub)
    args.append('--taskname')
    args.append(task)
    args.append('--runs')
    args += runs
    if not nofeat:
        args.append('--callfeat')
    return args


def main(argv=None):
    args = parse_command_line(argv)
    print(args)

    studyid = args.studyid
    specificruns = args.specificruns
    basedir = args.basedir
    modelname = args.modelname
    nofeat = args.nofeat

    sys_args_specificruns = args.specificruns  # specificruns passed in through argv

    # gets dictionary of study information
    study_info = specificruns
    hasSessions = False
    if specificruns == {}:  # if specificruns passed into command line was empty
        # tries getting study info first with hasSessions set to false
        # determines that hasSessions is true if the values of the subjects are empty
        mp_args = setup_utils.model_params_json_to_namespace(studyid, basedir, modelname)
        study_info = mp_args.specificruns

    l1 = list(study_info.keys())
    l2 = list(study_info[l1[0]].keys())[0]
    if l2.startswith('ses-'):
        hasSessions = True

    print(json.dumps(study_info))

    study_info_copy = copy.deepcopy(study_info)

    sys_argv = sys.argv[:]  # copy over the arguments passed in through the command line
    # remove the parameters that are not passed to mk_level2_fsf (keep everything that IS passed to mk_level2_fsf)
    params_to_remove = ['--email', '-e', '-A', '--account', '-t', '--time', '-N', '--nodes', '-s', '--specificruns',
                        '--outdir', '-M', '--mem']
    for param in params_to_remove:
        if param in sys_argv:
            i = sys_argv.index(param)
            del sys_argv[i]
            del sys_argv[i]
    if '--nofeat' in sys_argv:
        i = sys_argv.index('--nofeat')
        del sys_argv[i]
    del sys_argv[0]

    existing_feat_files = []
    jobs = []  # list of list of arguments to run mk_level2_fsf on
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
                    # check if feat exists for this run
                    model_subdir = '%s/model/level2/model-%s/%s/%s/task-%s' % (
                        os.path.join(basedir, studyid), modelname, subid, ses, task)
                    feat_file = "%s/%s_%s_task-%s.gfeat" % (model_subdir, subid, ses, task)
                    if sys_args_specificruns == {} and os.path.exists(
                            feat_file):  # if subject didn't pass in specificruns and a feat file for this task exists
                        print("WARNING: Existing feat file found: %s" % feat_file)
                        existing_feat_files.append(feat_file)
                        tasks_copy = study_info_copy[subid][ses]
                        tasks_copy.pop(task, None)  # removes the task from study_info_copy if a feat file was found
                    else:  # if subject passed in specificruns
                        if os.path.exists(feat_file):
                            existing_feat_files.append(feat_file)
                            print("WARNING: Existing feat file found: %s" % feat_file)
                        runs = study_info[subid][ses][task]
                        list.sort(runs)
                        args = sys_argv[:]  # copies over the list of arguments passed into the command line
                        args = add_args(args, sub, task, runs, nofeat)
                        args.append('--ses')
                        args.append(sesname)
                        jobs.append(args)
                if len(study_info_copy[subid][ses].keys()) == 0:  # if there are no tasks for this session
                    del study_info_copy[subid][ses]  # remove the session
                if len(study_info_copy[subid].keys()) == 0:  # if there are no sessions for this subject
                    del study_info_copy[subid]  # remove the subject from the dictionary
        else:  # no sessions
            tasks = sorted(study_info[subid].keys())
            for task in tasks:
                # check if feat exists for this run
                model_subdir = '%s/model/level2/model-%s/%s/task-%s' % (
                    os.path.join(basedir, studyid), modelname, subid, task)
                feat_file = "%s/%s_task-%s.gfeat" % (model_subdir, subid, task)
                if sys_args_specificruns == {} and os.path.exists(feat_file):
                    print("WARNING: Existing feat file found: %s" % feat_file)
                    existing_feat_files.append(feat_file)
                    tasks_copy = study_info_copy[subid]
                    tasks_copy.pop(task, None)  # remove the task from the dictionary if a feat file was found
                else:
                    if os.path.exists(feat_file):
                        existing_feat_files.append(feat_file)
                        print("WARNING: Existing feat file found: %s" % feat_file)
                    runs = study_info[subid][task]
                    list.sort(runs)
                    args = sys_argv[:]
                    args = add_args(args, sub, task, runs, nofeat)
                    jobs.append(args)
            if len(study_info_copy[subid].keys()) == 0:  # if there are no tasks for this subject
                del study_info_copy[subid]  # remove the subject from the dictionary

    additional_existing_feat_files = []
    # get additional existing feat files - any with + characters in their name
    for feat_file in existing_feat_files:
        upper_feat_dir = os.path.dirname(feat_file)
        dircontents = os.listdir(upper_feat_dir)
        for f in dircontents:
            if os.path.join(upper_feat_dir, f) not in existing_feat_files and len(os.path.split(f)) > 0 and \
                    os.path.split(f)[-1]:  # get file NAME without path
                filename = os.path.split(f)[-1]
                if filename.endswith('.gfeat'):
                    additional_existing_feat_files.append(os.path.join(upper_feat_dir, f))
                    print("WARNING: Existing feat file found: %s" % (os.path.join(upper_feat_dir, f)))

    existing_feat_files = existing_feat_files + additional_existing_feat_files

    if len(study_info_copy.keys()) == 0:
        print(
            "WARNING: All tasks for all subjects have been run on this model. Remove the feat files if you want to "
            "rerun them.")
        return existing_feat_files, jobs
    elif sys_args_specificruns == {} and len(
            existing_feat_files) != 0:  # if the user didn't pass in specificruns and existing feat files were found
        print(
            "WARNING: Some subjects' tasks have already been run on this model. If you want to rerun these subjects, "
            "remove their feat directories first. To run the remaining subjects, rerun run_level2.py and add:")
        print("-s \'%s\'" % (json.dumps(study_info_copy)))
        return existing_feat_files, jobs
    else:  # no existing feat files were found
        print(len(jobs), "jobs")
        return existing_feat_files, jobs


if __name__ == '__main__':
    main()
