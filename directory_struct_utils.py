"""
Gets information about the fmriprep directory structure
"""

# Created by Alice Xue, 06/2018

import os
import sys


def get_fmriprep_dir(studydir):
    """Checks for fmriprep directory under studydir

    Args:
        studydir (str): path of parent directory of fmriprep directory (basedir + studyid)
    Returns:
        path of fmriprep directory, if found, or empty string (prints error message)

    """
    fmriprep_dir = os.path.join(studydir, 'fmriprep')
    if os.path.exists(fmriprep_dir):
        return fmriprep_dir
    else:
        print("ERROR: fmriprep directory not found in %s" % studydir)
        sys.exit(-1)


def get_all_subs(studydir):
    """Gets list of subject IDs (not including the prefix 'sub-')

    Args:
        studydir (str): path of parent directory of fmriprep directory (basedir + studyid)
    Returns:
        sorted list of subjects

    """
    fmriprep = get_fmriprep_dir(studydir)
    all_subs = []
    if os.path.exists(fmriprep):
        folders = os.listdir(fmriprep)
        for folder in folders:
            if os.path.isdir(os.path.join(fmriprep, folder)) and folder.startswith('sub-'):
                i = folder.find('-')
                sub = folder[i + 1:]
                all_subs.append(sub)
        list.sort(all_subs)
    return all_subs


def get_runs(funcdir, task):
    """Gets list of runs for a given task
    Determines the run names based on files ending with '_preproc.nii.gz'
    Parses those file names (searches for _task- and _run-)

    Args:
        funcdir (str): path of func directory for a specific subject
        task: name of task to find runs for
    Returns:
        sorted list of run names for the given task and subject (subject is specified in funcdir)

    """
    runs = []
    files = os.listdir(funcdir)
    for f in files:
        if ('preproc' in f) and ('bold' in f) and ('brain' not in f):
            flag = '_task-' + task + '_run-'
            if flag in f:
                i1 = f.find(flag) + len(flag)
                tmp = f[i1:]
                i2 = tmp.find('_')
                run = tmp[:i2]
                if i1 > -1 and i2 > 0:
                    if run not in runs:
                        runs.append(run)
    list.sort(runs)
    return runs


def get_task_runs(funcdir):
    """Gets dictionary with task names as keys and list of runs as the values
    Determines the task names based on files ending with '_preproc.nii.gz'
    Parses those file names (searches for _task- and _run-)

    Args:
        funcdir (str): path of func directory for a specific subject
    Returns:
        dictionary (as stated above)

    """
    task_runs = {}
    if os.path.exists(funcdir):
        files = os.listdir(funcdir)
        for f in files:
            if ('preproc' in f) and ('bold' in f) and ('brain' not in f):
                # find task name
                flag = '_task-'
                if flag in f:
                    i1 = f.find(flag) + len(flag)
                    tmp = f[i1:]
                    i2 = tmp.find('_run-')
                    task = tmp[:i2]
                    if i1 > -1 and i2 > -1:
                        if task not in task_runs.keys():
                            # find runs for this task
                            task_runs[task] = get_runs(funcdir, task)
    return task_runs


"""
Return structure of fmriprep directory (see documentation below) and whether studydir BIDS directory has sessions 
"""


def get_study_info(studydir):
    hasSessions = False
    study_info = get_study_info_sessions_unknown(studydir, hasSessions)
    if len(study_info.keys()) > 0:
        if len(study_info[list(study_info.keys())[0]]) == 0:  # if empty
            hasSessions = True
            study_info = get_study_info_sessions_unknown(studydir, hasSessions)
    return study_info, hasSessions


def get_study_info_sessions_unknown(studydir, hasSessions):
    """Gets the structure of the fmriprep directory

    Args:
        studydir (str): path of parent directory of fmriprep directory (basedir + studyid)
        hasSessions: True if there are sessions for this study
    Returns:
        nested dictionary with subject IDs as the keys and then sessions (if they exist), task names, and list of runs

    """
    fmriprep = get_fmriprep_dir(studydir)
    all_subs = get_all_subs(studydir)
    info = {}
    for sub in all_subs:
        subdir = os.path.join(fmriprep, 'sub-' + sub)
        files = os.listdir(subdir)
        info['sub-' + sub] = {}
        if hasSessions:
            # info = {'sub-01':{'ses-01':{...}}}
            for f in files:  # session folders
                if os.path.isdir(os.path.join(subdir, f)) and f.startswith('ses-'):
                    funcdir = os.path.join(subdir, f, 'func')
                    info['sub-' + sub][f] = get_task_runs(funcdir)
        else:
            # info = {'sub-01':{'taskname':{...}}}
            funcdir = os.path.join(subdir, 'func')
            info['sub-' + sub] = get_task_runs(funcdir)
    return info
