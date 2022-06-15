#!/usr/bin/env python
""" mk_level3_fsf.py - make 3rd level (between-subjects) model
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

# Modified by Alice Xue, 06/2018

# create fsf file for arbitrary design

import argparse
from collections import OrderedDict
import inspect
import json

from directory_struct_utils import *
from openfmri_utils import *


def parse_command_line(argv):
    parser = argparse.ArgumentParser(argv, description='setup_task')

    parser.add_argument('--studyid', dest='studyid',
                        required=True, help='Study ID')
    parser.add_argument('--subs', dest='subids', nargs='+',
                        default=[], help='subject identifiers (not including prefix "sub-")')
    parser.add_argument('--taskname', dest='taskname',
                        required=True, help='Task name')
    parser.add_argument('--basedir', dest='basedir',
                        required=True, help='Base directory (above studyid directory)')
    parser.add_argument('-m', '--modelname', dest='modelname',
                        required=True, help='Model name')
    parser.add_argument('--sesname', dest='sesname',
                        default='', help='Name of session (not including "ses-")')
    parser.add_argument('--randomise', dest='randomise', action='store_true',
                        default=False, help='Use Randomise for stats instead of FLAME 1')

    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = parse_command_line(argv)
    print(args)

    mk_level3_fsf(args)


# a: Namespace object, output of parser_command_line
def mk_level3_fsf(a):
    # attributes in a:
    # studyid,subids,taskname,basedir,modelname,sesname,randomise

    # Set up directories
    _thisDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    studydir = os.path.join(a.basedir, a.studyid)

    modeldir = '%s/model/level3/model-%s' % (studydir, a.modelname)
    if a.sesname != '':
        modeldir += '/ses-%s' % a.sesname
    modeldir = os.path.join(modeldir, 'task-%s' % a.taskname)
    if not os.path.exists(modeldir):
        os.makedirs(modeldir)

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
        if a.taskname in cond_key.keys():
            cond_key = cond_key[a.taskname]
        else:
            print(
                "WARNING: Task name %s was not found in JSON file %s. Make sure the JSON file is formatted correctly" %
                (a.taskname, cond_key_json))
            return []  # no fsf files created
            # an empty list is returned (rather than an error thrown) because this function is called by
            # mk_all_level3_fsf, which needs to know how many fsf's were created
        nconditions = len(cond_key.keys())
    elif os.path.exists(cond_key_txt):
        cond_key = load_condkey(cond_key_txt)
        conditions = cond_key[a.taskname].values()
        nconditions = len(conditions)  # TO DO: test this
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
            os.path.join(studydir, a.studyid, 'model/level1/model-%s' % a.modelname)))
        all_addl_contrasts = {}
    if a.taskname in all_addl_contrasts:
        addl_contrasts = all_addl_contrasts[a.taskname]
        n_addl_contrasts = len(addl_contrasts)
    else:
        n_addl_contrasts = 0

    # figure out the number of copes
    ncopes = nconditions + 1 + n_addl_contrasts

    # get fsf template with default values
    stubfilename = os.path.join(_thisDir, 'design_level3.stub')
    customstubfilename = os.path.join(a.basedir, a.studyid,
                                      'model/level3/model-%s/design_level3_custom.stub' % a.modelname)
    # Get settings from custom stub file, store in customsettings dictionary 
    # in customsettings, key is the setting ('fmri(mc)' for example) and the value of the setting is the value
    customsettings = {}
    customsettings_fromstub = {}
    if os.path.exists(customstubfilename):
        print('Found custom fsf stub')
        customstubfile = open(customstubfilename, 'r')
        for line in customstubfile:
            llist = line.split(' ')
            if len(line) > 3 and llist[0] == 'set':
                setting = llist[1]
                value = llist[2]
                customsettings[setting] = value
                customsettings[setting] = True
        customstubfile.close()

    if a.randomise:
        if 'fmri(mixed_yn)' in customsettings and customsettings['fmri(mixed_yn'] == 4:
            print(
                'ERROR: design_level3_custom.stub conflicts with the command line argument randomise. Modify the '
                'custom stub file or don\'t pass --randomise into the command line.')
            sys.exit(-1)
        customsettings['fmri(mixed_yn)'] = '4\n'
        customsettings_fromstub['fmri(mixed_yn)'] = False
        if 'fmri(randomisePermutations)' not in customsettings:
            customsettings['fmri(randomisePermutations)'] = '5000\n'
            customsettings_fromstub['fmri(randomisePermutations)'] = False
        if 'fmri(thresh)' not in customsettings:
            customsettings['fmri(thresh)'] = '4\n'
            customsettings_fromstub['fmri(thresh)'] = False

    fsfnames = []
    for copenum in range(1, ncopes + 1):
        # set feat names
        if a.sesname != '':
            outfilename = '%s/ses-%s_task-%s_cope-%03d.fsf' % (modeldir, a.sesname, a.taskname, copenum)
        else:
            outfilename = '%s/task-%s_cope-%03d.fsf' % (modeldir, a.taskname, copenum)
        fsfnames.append(outfilename)
        outfile = open(outfilename, 'w')
        outfile.write('# Automatically generated by mk_fsf.py\n')

        # first get common lines from stub file
        stubfile = open(stubfilename, 'r')
        for line in stubfile:
            llist = line.split(' ')
            if len(line) > 3 and llist[0] == 'set':
                setting = llist[1]
                # check if setting in default stub file shows up in custom stub file
                if setting in customsettings.keys():
                    if customsettings_fromstub[setting]:
                        outfile.write('# From custom stub file\n')
                    llist[2] = customsettings[setting]  # set the value of the setting
                    line = ' '.join(llist)
                    del customsettings[setting]
            outfile.write(line)
        stubfile.close()

        # if there are other settings that haven't been replaced and still need to be added
        if len(customsettings) > 0:
            for setting in customsettings:
                if customsettings_fromstub[setting]:
                    outfile.write('\n# Additional setting from custom stub file ###\n')
                if setting == 'fmri(randomisePermutations)':
                    outfile.write('\n# Higher-level permutations\n')
                line = 'set ' + setting + ' ' + customsettings[setting]
                outfile.write(line)

        # now add custom lines

        outfile.write('\n\n### AUTOMATICALLY GENERATED PART###\n\n')

        # look for standard brain provided by fsl (need fsl's path)
        env = os.environ.copy()
        FSLDIR = '/usr/local/fsl'
        if 'FSLDIR' in env.keys():
            FSLDIR = env["FSLDIR"]
        elif 'FSL_DIR' in env.keys():
            FSLDIR = env["FSL_DIR"]
        regstandard = os.path.join(FSLDIR, 'data/standard/MNI152_T1_2mm_brain')
        outfile.write('set fmri(regstandard) "%s"\n' % regstandard)

        outfile.write('set fmri(outputdir) "%s/cope-%03d.gfeat"\n' % (modeldir, copenum))

        ngoodsubs = 0
        # use the list of subs passed to this function, or get list of all subs
        if len(a.subids) == 0:
            sublist = get_all_subs(studydir)
        else:
            sublist = a.subids

        missing_feat_files = []

        # iterate through all subjects
        for sub in sublist:  # sub doesn't include prefix 'sub-'
            subid_ses = "sub-" + sub
            subid_ses_dir = "sub-" + sub
            if a.sesname != "":
                subid_ses += "_ses-%s" % a.sesname
                subid_ses_dir += "/ses-%s" % a.sesname
            featfile = os.path.join(studydir, 'model/level2/model-%s/%s/task-%s/%s_task-%s.gfeat/cope%d.feat' % (
                a.modelname, subid_ses_dir, a.taskname, subid_ses, a.taskname, copenum))
            if os.path.exists(featfile):
                outfile.write('set feat_files(%d) "%s"\n' % (ngoodsubs + 1, featfile))
                outfile.write('set fmri(evg%d.1) 1\n' % int(ngoodsubs + 1))
                outfile.write('set fmri(groupmem.%d) 1\n' % int(ngoodsubs + 1))
                ngoodsubs += 1
            else:
                missing_feat_files.append(featfile)

        if ngoodsubs == 0:
            print("ERROR: No subjects with feat files found for cope%d" % copenum)
        elif len(missing_feat_files) > 0:
            for featfile in missing_feat_files:
                print("WARNING: featfile not found: %s, was not added to *.fsf\n" % featfile)

        # Note: "feat won't run if zero feat_files are added to this fsf."
        outfile.write('set fmri(npts) %d\n' % ngoodsubs)  # number of runs
        outfile.write('set fmri(multiple) %d\n' % ngoodsubs)  # number of runs

        outfile.close()

    """
    for f in fsfnames:
        print f
    """

    return fsfnames


if __name__ == '__main__':
    main()
