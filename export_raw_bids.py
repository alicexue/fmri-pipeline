#!/usr/bin/env python
"""
Exports raw BIDS from flywheel for all subjects into a directory called 'raw'
(unable to get list of subjects to export bids directories individually)
Subject codes are passed as parameters to "fw export bids" not subject id's 
Subject codes and id's may differ if subjects codes contain underscores 
(I assume that subject id's are subjects codes with underscores removed)
Note: raw BIDS can only be exported if docker is running
"""

# Created by Alice Xue, 06/2018

import flywheel
import subprocess as sp
import sys
import os

import directory_struct_utils


def main():
    if len(sys.argv) != 6:
        print(
            "usage: export_raw_bids <studyid> <basedir> <Flywheel API key> <Flywheel group_id> <Flywheel project_label>"
        )
        sys.exit(-1)
    studyid = sys.argv[1]
    basedir = sys.argv[2]
    key = sys.argv[3]
    group_id = sys.argv[4]
    project_label = sys.argv[5]
    export_raw_bids(studyid, basedir, key, group_id, project_label)


def export_raw_bids(studyid, basedir, key, group_id, project_label):
    studydir = os.path.join(basedir, studyid)
    rawdir = os.path.join(studydir, 'raw')
    if not os.path.exists(rawdir):
        os.makedirs(rawdir)

    # checks whether docker is installed (but not if docker is running)
    try:
        FNULL = open(os.devnull, 'w')
        sp.call(['docker'], stdout=FNULL, stderr=sp.STDOUT)
        dockerExists = True
    except FileNotFoundError:
        dockerExists = False

    # check if fw CLI is installed - needed for exporting BIDS
    try:
        FNULL = open(os.devnull, 'w')
        sp.call(['fw'], stdout=FNULL, stderr=sp.STDOUT)
        fwExists = True
    except FileNotFoundError:
        fwExists = False

    print('\n## Exporting raw BIDS now ##\n')

    if fwExists and dockerExists:
        # Create client
        fw = flywheel.Client(key)  # API key

        sub_codes = []

        for project in fw.get_group_projects(group_id):
            if project.label == project_label:
                print('Project: %s: %s' % (project.id, project.label))
                for session in fw.get_project_sessions(project.id):
                    sub = session.subject.code
                    if sub not in sub_codes:
                        sub_codes.append(session.subject.code)

        all_subs = directory_struct_utils.get_all_subs(studydir)  # subjects with fmriprep outputs downloaded
        sub_code_dict = {}
        for code in sub_codes:
            code_w_underscore_removed = code.replace("_", "")
            # want to removed underscore from subject code because underscore in subject id is not compatible with BIDS
            if code_w_underscore_removed in all_subs:
                sub_code_dict[code] = code_w_underscore_removed  # key is subject code, value is subject id
            # subject code is used to export BIDS, subject id used by the fmriprep output

        sub_list = sorted(sub_code_dict.keys())
        for sub_code in sub_list:
            sub = sub_code_dict[sub_code]
            rawsubdir = os.path.join(rawdir, 'sub-%s' % sub)
            if os.path.exists(rawsubdir):
                print("Skipping download of raw bids for sub-%s" % sub)
            else:
                # creates tmp dir specific to the subject
                tmpsubdir = os.path.join(studydir, 'tmp_sub-%s_BIDS' % sub)
                os.mkdir(tmpsubdir)
                # call subprocess to export BIDS
                commands = ['fw', 'export', 'bids', tmpsubdir, '-p', project_label, '--subject', sub_code]
                print('Calling:', ' '.join(commands))
                sp.call(commands)
                # moves the exported directory into the raw directory
                rawsubout = os.path.join(tmpsubdir, 'sub-%s' % sub)
                print('Moving %s to %s' % (rawsubout, rawdir))
                sp.call(['mv', rawsubout, rawdir])
                # removes tmp directory that was created
                print('Removing %s' % tmpsubdir)
                sp.call(['rm', '-rf', tmpsubdir])
    else:
        if not fwExists:
            print('Flywheel CLI is not installed, which is required for exporting raw BIDS.')
        if not dockerExists:
            print('Docker is not installed. Docker is required to export raw BIDS from flywheel')


if __name__ == '__main__':
    main()
