"""
Get information to run mk_level3_fsf on multiple subjects, tasks, runs, etc
Called by run_level3_feat.py
"""
# Created by Alice Xue, 06/2018

import argparse
import json

from directory_struct_utils import *
import mk_level3_fsf
import setup_utils


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='setup_jobs')
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',help='an integer for the accumulator')
    # set up boolean flags

    parser.add_argument('--studyid', dest='studyid',
                        required=True, help='Study ID')
    parser.add_argument('--basedir', dest='basedir',
                        required=True, help='Base directory (above studyid directory)')
    parser.add_argument('-m', '--modelname', dest='modelname',
                        required=True, help='Model name')
    parser.add_argument('--subs', dest='subids', nargs='+',
                        default=[], help='subject identifiers (not including prefix "sub-")')
    parser.add_argument('--randomise', dest='randomise', action='store_true',
                        default=False, help='Use Randomise for stats instead of FLAME 1')
    parser.add_argument('--nofeat', dest='nofeat', action='store_true',
                        default=False, help='Only create the fsf\'s, don\'t call feat')

    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = parse_command_line(argv)
    print(args)

    studyid = args.studyid
    basedir = args.basedir
    modelname = args.modelname
    subids = args.subids
    randomise = args.randomise

    # gets dictionary of study information
    hasSessions = False
    mp_args = setup_utils.model_params_json_to_namespace(studyid, basedir, modelname)
    study_info = mp_args.specificruns

    l1 = list(study_info.keys())
    l2 = list(study_info[l1[0]].keys())[0]
    if l2.startswith('ses-'):
        hasSessions = True

    print(json.dumps(study_info))

    jobs = []
    if len(subids) == 0:  # checks if user did not specify subjects to run level 3 on
        subs = list(study_info.keys())
    else:
        subs = []
        for sub in subids:
            subs.append('sub-' + sub)  # adds the prefix 'sub-' to each subid passed in
    list.sort(subs)
    # iterate through runs based on the runs the first subject did
    subid = subs[0]
    if hasSessions:
        sessions = sorted(study_info[subid].keys())
        for ses in sessions:
            sesname = ses[len('ses-'):]  # remove prefix 'ses-'
            tasks = sorted(study_info[subid][ses].keys())
            for task in tasks:
                args = argparse.Namespace()
                args.studyid = studyid
                args.subids = subids
                args.taskname = task
                args.basedir = basedir
                args.modelname = modelname
                args.sesname = sesname
                args.randomise = randomise
                jobs.append(args)
    else:
        sesname = ''
        tasks = sorted(study_info[subid].keys())
        for task in tasks:
            args = argparse.Namespace()
            args.studyid = studyid
            args.subids = subids
            args.taskname = task
            args.basedir = basedir
            args.modelname = modelname
            args.sesname = sesname
            args.randomise = randomise
            jobs.append(args)

    # creates fsf's and retrieves a list of their names
    all_copes = []
    for job_args in jobs:
        copes = mk_level3_fsf.mk_level3_fsf(job_args)
        all_copes += copes

    # find existing cope gfeats
    existing_copes = []
    for cope_fsf in all_copes:
        upper_cope_dir = os.path.dirname(cope_fsf)
        dircontents = os.listdir(upper_cope_dir)

        filename = os.path.split(cope_fsf)[-1]
        if 'cope-' in filename:
            i = cope_fsf.find('_cope-')
            cope_gfeat_name = cope_fsf[i + 1:-1 * len('.fsf')]
            cope_gfeat = cope_gfeat_name + '.gfeat'
            cope_gfeat_path = os.path.join(upper_cope_dir, cope_gfeat)
            if cope_gfeat in dircontents:
                existing_copes.append(cope_gfeat_path)
                print("WARNING: Existing cope found here: %s" % cope_gfeat_path)
            for f in dircontents:
                if f.startswith(cope_gfeat_name) and f.endswith('.gfeat') and f not in existing_copes:
                    existing_copes.append(os.path.join(upper_cope_dir, f))

    if len(existing_copes) == 0:
        print(len(all_copes), "jobs")
    return existing_copes, all_copes


if __name__ == '__main__':
    main()
