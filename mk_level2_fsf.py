#!/usr/bin/env python
"""mk_level2_fsf.py - make 2nd level (between-runs) fixed effect model
"""

## Copyright 2011, Russell Poldrack. All rights reserved.

## Redistribution and use in source and binary forms, with or without modification, are
## permitted provided that the following conditions are met:

##    1. Redistributions of source code must retain the above copyright notice, this list of
##       conditions and the following disclaimer.

##    2. Redistributions in binary form must reproduce the above copyright notice, this list
##       of conditions and the following disclaimer in the documentation and/or other materials
##       provided with the distribution.

## THIS SOFTWARE IS PROVIDED BY RUSSELL POLDRACK ``AS IS'' AND ANY EXPRESS OR IMPLIED
## WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
## FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL RUSSELL POLDRACK OR
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
## CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
## SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
## ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
## NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Modified by Alice Xue to work with BIDS-like structure 06/2018

# create fsf file for arbitrary design

import argparse
from collections import OrderedDict
import inspect
import json
import subprocess as sub
import sys

from openfmri_utils import *


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='setup_subject')

    parser.add_argument('--studyid', dest='studyid',
                        required=True, help='Study ID')
    parser.add_argument('--sub', dest='subid',
                        required=True, help='subject identifier (not including prefix "sub-")')
    parser.add_argument('--taskname', dest='taskname',
                        required=True, help='Task name')
    parser.add_argument('--runs', dest='runs', nargs='+',
                        required=True, help='Runs')
    parser.add_argument('--basedir', dest='basedir',
                        required=True, help='Base directory (above studyid directory)')
    parser.add_argument('-m', '--modelname', dest='modelname',
                        required=True, help='Model name')
    parser.add_argument('--sesname', dest='sesname',
                        default='', help='Name of session (not including "ses-")')
    parser.add_argument('--callfeat', dest='callfeat', action='store_true',
                        default=False, help='Call fsl\'s feat on the .fsf file that is created')

    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = parse_command_line(argv)
    print(args)

    mk_level2_fsf(args)


# a: Namespace object, output of parser_command_line
def mk_level2_fsf(a):
    # attributes in a:
    # studyid,subid,taskname,runs,basedir,modelname,sesname,callfeat

    _thisDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    # set up variables 
    subid = 'sub-%s' % a.subid
    subid_ses = subid
    if a.sesname != "":
        subid_ses += "_ses-%s" % (
            a.sesname)  # for if files are prefixed with with the name of the session after the subject ID

    # locate level 1 model dir, create level 2 model dir
    lev1_model_subdir = '%s/model/level1/model-%s/%s' % (os.path.join(a.basedir, a.studyid), a.modelname, subid)
    model_subdir = '%s/model/level2/model-%s/%s' % (os.path.join(a.basedir, a.studyid), a.modelname, subid)
    if a.sesname != '':
        lev1_model_subdir += '/ses-%s' % a.sesname
        model_subdir += '/ses-%s' % a.sesname
    model_subdir = os.path.join(model_subdir, 'task-%s' % a.taskname)
    if not os.path.exists(model_subdir):
        os.makedirs(model_subdir)

    ## read the conditions_key file
    # if it's a json file
    cond_key_json = os.path.join(a.basedir, a.studyid, 'model/level1/model-%s/condition_key.json' % a.modelname)
    # if it's a text file
    cond_key_txt = os.path.join(a.basedir, a.studyid, 'model/level1/model-%s/condition_key.txt' % a.modelname)
    if os.path.exists(cond_key_json):
        try:
            cond_key = json.load(open(cond_key_json),
                             object_pairs_hook=OrderedDict)  # keep the order of the keys as they were in the json file
        except ValueError:
            print("\nERROR: Could not read the %s file. Make sure it is formatted correctly." % cond_key_json)
            sys.exit(-1)
        conddict_keys = []
        if a.taskname in cond_key.keys():
            # set conddict to the dictionary for this task where 
            # the EV names are the keys
            # and the names of the conditions are the values
            cond_key = cond_key[a.taskname]
            for key, value in cond_key.items():
                conddict_keys.append(key)
        else:
            print("ERROR: Task name was not found in JSON file %s. Make sure the JSON file is formatted correctly" % (
                cond_key_json))
            sys.exit(-1)

        ev_keys = conddict_keys
        ev_files = []
        conditions = []
        # get the EV file names and the condition names
        for ev in ev_keys:
            ev_files.append('%s_task-%s_run-%s_ev-%03d' % (subid_ses, a.taskname, a.runs[0], int(ev)))
            conditions.append(cond_key[ev])
    elif os.path.exists(cond_key_txt):
        cond_key = load_condkey(cond_key_txt)
        cond_key = cond_key[a.taskname]
    else:
        print("ERROR: Could not find condition key in %s" % (
            os.path.join(a.basedir, a.studyid, 'model/level1/model-%s' % a.modelname)))
        sys.exit(-1)

    ## get contrasts
    # if it's a json file
    contrastsfile_json = os.path.join(a.basedir, a.studyid, 'model/level1/model-%s/task_contrasts.json' % a.modelname)
    # if it's a txt file
    contrastsfile_txt = os.path.join(a.basedir, a.studyid, 'model/level1/model-%s/task_contrasts.txt' % a.modelname)
    if os.path.exists(contrastsfile_json):
        try:
            all_addl_contrasts = json.load(open(contrastsfile_json), object_pairs_hook=OrderedDict)
        except ValueError:
            print("\nERROR: Could not read the %s file. Make sure it is formatted correctly." % contrastsfile_json)
            sys.exit(-1)
        # all_addl_contrasts = dict(all_addl_contrasts)
        # for contrast in all_addl_contrasts:
        #    all_addl_contrasts[contrast] = dict(all_addl_contrasts[contrast])
    elif os.path.exists(contrastsfile_txt):
        all_addl_contrasts = load_contrasts(contrastsfile_txt)
    else:
        print("WARNING: Could not find task_contrasts file in %s" % (
            os.path.join(a.basedir, a.studyid, 'model/level1/model-%s' % a.modelname)))
        all_addl_contrasts = {}
    if a.taskname in all_addl_contrasts:
        addl_contrasts = all_addl_contrasts[a.taskname]
        n_addl_contrasts = len(addl_contrasts)
    else:
        n_addl_contrasts = 0

    nruns = len(a.runs)

    # get fsf template with default values
    stubfilename = os.path.join(_thisDir, 'design_level2.stub')
    customstubfilename = os.path.join(a.basedir, a.studyid,
                                      'model/level2/model-%s/design_level2_custom.stub' % a.modelname)
    outfilename = os.path.join(model_subdir, '%s_task-%s.fsf' % (subid_ses, a.taskname))
    outfile = open(outfilename, 'w')
    outfile.write('# Automatically generated by mk_fsf.py\n')

    # Get settings from custom stub file, store in customsettings dictionary 
    # in customsettings, key is the setting ('fmri(mc)' for example) and the value of the setting is the value
    customsettings = {}
    if os.path.exists(customstubfilename):
        print('Found custom fsf stub')
        customstubfile = open(customstubfilename, 'r')
        for line in customstubfile:
            llist = line.split(' ')
            if len(line) > 3 and llist[0] == 'set':
                setting = llist[1]
                value = llist[2]
                customsettings[setting] = value
        customstubfile.close()

    # first get common lines from stub file
    stubfile = open(stubfilename, 'r')
    for line in stubfile:
        llist = line.split(' ')
        if len(line) > 3 and llist[0] == 'set':
            setting = llist[1]
            # check if setting in default stub file shows up in custom stub file
            if setting in customsettings.keys():
                outfile.write('# From custom stub file\n')
                llist[2] = customsettings[setting]  # set the value of the setting
                line = ' '.join(llist)
                del customsettings[setting]
        outfile.write(line)
    stubfile.close()

    # if there are other settings that haven't been replaced and still need to be added
    if len(customsettings) > 0:
        outfile.write('\n### Additional settings from custom stub file ###\n')
        for setting in customsettings:
            line = 'set ' + setting + ' ' + customsettings[setting]
            outfile.write(line)

    # now add custom lines

    # first check for empty EV file
    empty_evs = []
    for r in range(nruns):
        empty_ev_file = "%s/task-%s_run-%s/onsets/%s_task-%s_run-%s_empty_evs.txt" % (
            lev1_model_subdir, a.taskname, a.runs[r], subid_ses, a.taskname, a.runs[r])
        if os.path.exists(empty_ev_file):
            evfile = open(empty_ev_file, 'r')
            # edited to extend pre-existing list with new list (12.08.22 - cvg)
            empty_evs.extend([int(x.strip()) for x in evfile.readlines()])
            evfile.close()

    outfile.write('\n\n### AUTOMATICALLY GENERATED PART###\n\n')

    # look for standard brain fsl provides
    env = os.environ.copy()
    FSLDIR = '/usr/local/fsl'
    if 'FSLDIR' in env.keys():
        FSLDIR = env["FSLDIR"]
    elif 'FSL_DIR' in env.keys():
        FSLDIR = env["FSL_DIR"]
    regstandard = os.path.join(FSLDIR, 'data/standard/MNI152_T1_2mm_brain')
    outfile.write('set fmri(regstandard) "%s"\n' % regstandard)

    outfile.write('set fmri(outputdir) "%s/%s_task-%s.gfeat"\n' % (model_subdir, subid_ses, a.taskname))
    outfile.write('set fmri(npts) %d\n' % nruns)  # number of runs
    outfile.write('set fmri(multiple) %d\n' % nruns)  # number of runs
    outfile.write('set fmri(ncopeinputs) %d\n' % int(len(cond_key) + 1 + n_addl_contrasts))  # number of copes

    # iterate through runs
    for r in range(nruns):
        # check that feat folder for this run for this subject exists in the level 1 directory
        feat_folder = "%s/task-%s_run-%s/%s_task-%s_run-%s.feat" % (
            lev1_model_subdir, a.taskname, a.runs[r], subid_ses, a.taskname, a.runs[r])
        if not os.path.exists(feat_folder):
            print("ERROR: Feat folder for level 1 analysis does not exist here: %s" % feat_folder)
            sys.exit(-1)

        feat_folder_loc = "%s/task-%s_run-%s" % (lev1_model_subdir, a.taskname, a.runs[r])
        folders = os.listdir(feat_folder_loc)
        feat_folders = []
        for f in folders:
            if f.startswith('%s_task-%s_run-%s' % (subid_ses, a.taskname, a.runs[r])) and f.endswith('.feat'):
                feat_folders.append(f)
        if len(feat_folders) > 1:
            print("WARNING: Multiple feat folders found. Using %s" % feat_folder)

        # check if registration was run during level 1 analysis, and if workaround needs to be done
        if not os.path.exists(feat_folder + '/reg'):
            print("Registration was not run during first level analysis. reg folder missing in %s" % feat_folder)
            print("Doing registration workaround...")
            # http://mumfordbrainstats.tumblr.com/post/166054797696/feat-registration-workaround
            print("Creating reg folder...")
            sub.call(['mkdir', feat_folder + '/reg'])
            if os.path.exists(feat_folder + '/reg_standard'):
                print("Deleting reg_standard from %s ..." % feat_folder)
                sub.call(['rm', '-rf', feat_folder + '/reg_standard'])
            sub.call(['rm', '-f', feat_folder + '/reg/' + '*.mat'])

            env = os.environ.copy()

            if 'FSLDIR' in env.keys():
                ident_file = os.path.join(env["FSLDIR"], "etc/flirtsch/ident.mat")
            elif 'FSL_DIR' in env.keys():
                ident_file = os.path.join(env["FSL_DIR"], "etc/flirtsch/ident.mat")
            else:
                print("ERROR: No example_func2standard.mat found. Make sure $FSL_DIR or $FSLDIR are defined")
                sys.exit(-1)

            print("Copying %s to %s" % (ident_file, feat_folder + '/reg'))
            sub.call(['cp', ident_file, feat_folder + '/reg/example_func2standard.mat'])

            mean_func = 'mean_func.nii.gz'
            if os.path.exists(feat_folder + '/' + mean_func):
                print("Copying %s to %s" % (mean_func, feat_folder + '/reg'))
                sub.call(['cp', feat_folder + '/' + mean_func, feat_folder + '/reg/standard.nii.gz'])
            else:
                print("No %s found in %s." % (mean_func, feat_folder))
            print("Completed registration workaround.")

        outfile.write('set feat_files(%d) "%s"\n' % (int(r + 1), feat_folder))
        outfile.write('set fmri(evg%d.1) 1\n' % int(r + 1))
        outfile.write('set fmri(groupmem.%d) 1\n' % int(r + 1))

    # need to figure out if any runs have empty EVs and leave them out
    for c in range(len(cond_key) + 1 + n_addl_contrasts):
        if not c + 1 in empty_evs:
            outfile.write('set fmri(copeinput.%d) 1\n' % int(c + 1))
        else:
            outfile.write('set fmri(copeinput.%d) 0\n' % int(c + 1))

    outfile.close()

    print('outfilename: ' + outfilename)

    if a.callfeat:
        featargs = ["feat", outfilename]
        print("Calling", ' '.join(featargs))
        sub.call(featargs)

    return outfilename


if __name__ == '__main__':
    main()
