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
import json
import numpy as N
import os
import subprocess as sub
import sys

from directory_struct_utils import *
from openfmri_utils import *

def parse_command_line(argv):
    parser = argparse.ArgumentParser(argv, description='setup_task')

    parser.add_argument('--studyid', dest='studyid',
        required=True,help='Study ID')
    parser.add_argument('--subs', dest='subids', nargs='+',
        default=[],help='subject identifiers (not including prefix "sub-")')
    parser.add_argument('--taskname', dest='taskname',
        required=True,help='Task name')
    parser.add_argument('--basedir', dest='basedir',
        required=True,help='Base directory (above studyid directory)')
    parser.add_argument('-m', '--modelname', dest='modelname',
        required=True,help='Model name')
    parser.add_argument('--sesname', dest='sesname',
        default='',help='Name of session (not including "ses-")')
    
    args = parser.parse_args(argv)
    return args

def main(argv=None):
    args=parse_command_line(argv)
    print args
    
    studyid=args.studyid
    subids=args.subids
    taskname=args.taskname
    basedir=args.basedir
    modelname=args.modelname
    sesname=args.sesname
      
    mk_level3_fsf(studyid,subids,taskname,basedir,modelname,sesname)


def mk_level3_fsf(studyid,subids,taskname,basedir,modelname,sesname):
    # Set up directories
    _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
    studydir=os.path.join(basedir,studyid)

    modeldir='%s/model/level3/model-%s'%(studydir,modelname)
    if sesname!='':
        modeldir+='/ses-%s'%(sesname)
    modeldir=os.path.join(modeldir,'task-%s'%taskname)
    if not os.path.exists(modeldir):
        os.makedirs(modeldir)

    ## read the conditions_key file
    # if it's a json file
    cond_key_json = os.path.join(basedir,studyid,'model/level1/model-%s/condition_key.json'%modelname)
    # if it's a text file
    cond_key_txt = os.path.join(basedir,studyid,'model/level1/model-%s/condition_key.txt'%modelname)
    if os.path.exists(cond_key_json):
        cond_key = json.load(open(cond_key_json), object_pairs_hook=OrderedDict) # keep the order of the keys as they were in the json file 
        if taskname in cond_key.keys():
            cond_key = cond_key[taskname]
        else:
            print "WARNING: Task name %s was not found in JSON file %s. Make sure the JSON file is formatted correctly"%(taskname,cond_key_json)
            return [] # no fsf files created
            # an empty list is returned (rather than an error thrown) because this function is called by mk_all_level3_fsf, which needs to know how many fsf's were created
        nconditions = len(cond_key.keys())
    elif os.path.exists(cond_key_txt):
        cond_key=load_condkey(cond_key_txt)
        conditions=cond_key[taskname].values()
        cond_key = cond_key[taskname]
    else:
        print "ERROR: Could not find condition key in %s"%(os.path.join(basedir,studyid,'model/level1/model-%s'%modelname))
        sys.exit(-1)

    ## get contrasts
    # if it's a json file
    contrastsfile_json=os.path.join(basedir,studyid,'model/level1/model-%s/task_contrasts.json'%modelname)
    # if it's a txt file
    contrastsfile_txt=os.path.join(basedir,studyid,'model/level1/model-%s/task_contrasts.txt'%modelname)
    if os.path.exists(contrastsfile_json):
        all_addl_contrasts = json.load(open(contrastsfile_json), object_pairs_hook=OrderedDict)
        all_addl_contrasts = dict(all_addl_contrasts)
        for contrast in all_addl_contrasts:
            all_addl_contrasts[contrast] = dict(all_addl_contrasts[contrast])
    elif os.path.exists(contrastsfile_txt):
        all_addl_contrasts=load_contrasts(contrastsfile)
    else:
        print "WARNING: Could not find task_contrasts file in %s"%(os.path.join(studydir,studyid,'model/level1/model-%s'%modelname))
        all_addl_contrasts={}
    if all_addl_contrasts.has_key(taskname):
        addl_contrasts=all_addl_contrasts[taskname]
        n_addl_contrasts=len(addl_contrasts)
    else:
        n_addl_contrasts=0

    # figure out the number of copes
    ncopes=nconditions+1+n_addl_contrasts

    # get fsf template with default values
    stubfilename=os.path.join(_thisDir,'design_level3.stub')
    customstubfilename=os.path.join(basedir,studyid,'model/level3/model-%s/design_level3_custom.stub'%modelname)
    # Get settings from custom stub file, store in customsettings dictionary 
    # in customsettings, key is the setting ('fmri(mc)' for example) and the value of the setting is the value
    customsettings={}
    if os.path.exists(customstubfilename):
        print 'Found custom fsf stub'
        customstubfile=open(customstubfilename,'r')
        for l in customstubfile:
            llist=l.split(' ')
            if len(l)>3 and llist[0]=='set':
                setting=llist[1]
                value=llist[2]
                customsettings[setting]=value
        customstubfile.close()

    fsfnames=[]
    for copenum in range(1,ncopes+1):
        # set feat names
        if sesname!='':
            outfilename='%s/ses-%s_task-%s_cope-%03d.fsf'%(modeldir,sesname,taskname,copenum)
        else:
            outfilename='%s/task-%s_cope-%03d.fsf'%(modeldir,taskname,copenum)
        fsfnames.append(outfilename)
        outfile=open(outfilename,'w')
        outfile.write('# Automatically generated by mk_fsf.py\n')

        # first get common lines from stub file
        stubfile=open(stubfilename,'r')
        for l in stubfile:
            llist=l.split(' ')
            if len(l)>3 and llist[0]=='set':
                setting=llist[1]
                value=llist[2]
                # check if setting in default stub file shows up in custom stub file
                if setting in customsettings.keys():
                    outfile.write('# From custom stub file\n')
                    llist[2]=customsettings[setting]
                    l=' '.join(llist)
                    del customsettings[setting]
            outfile.write(l)
        stubfile.close()

         # if there are other settings that haven't been replaced and still need to be added
        if len(customsettings) > 0:
            outfile.write('\n### Additional settings from custom stub file ###\n')
            for setting in customsettings:
                l='set ' + setting + ' ' + customsettings[setting]
                outfile.write(l)

        # now add custom lines

        outfile.write('\n\n### AUTOMATICALLY GENERATED PART###\n\n')

        # look for standard brain provided by fsl (need fsl's path)
        env = os.environ.copy()
        FSLDIR='/usr/local/fsl'
        if 'FSLDIR' in env.keys():
            FSLDIR=env["FSLDIR"]
        elif 'FSL_DIR' in env.keys():
            FSLDIR=env["FSL_DIR"]
        regstandard=os.path.join(FSLDIR,'data/standard/MNI152_T1_2mm_brain')
        outfile.write('set fmri(regstandard) "%s"\n'%regstandard)

        outfile.write('set fmri(outputdir) "%s/cope-%03d.gfeat"\n'%(modeldir,copenum))

        ngoodsubs=0
        # use the list of subs passed to this function, or get list of all subs
        if len(subids)==0:
            sublist=get_all_subs(studydir)
        else:
            sublist=subids

        # iterate through all subjects
        for sub in sublist: # sub doesn't include prefix 'sub-'
            subid_ses="sub-"+sub
            subid_ses_dir="sub-"+sub
            if sesname!="":
                subid_ses+="_ses-%s"%(sesname)
                subid_ses_dir+="/ses-%s"%(sesname)
            featfile=os.path.join(studydir,'model/level2/model-%s/%s/task-%s/%s_task-%s.gfeat/cope%d.feat'%(modelname,subid_ses_dir,taskname,subid_ses,taskname,copenum))
            if os.path.exists(featfile):
                outfile.write('set feat_files(%d) "%s"\n'%(ngoodsubs+1,featfile))
                outfile.write('set fmri(evg%d.1) 1\n'%int(ngoodsubs+1))
                outfile.write('set fmri(groupmem.%d) 1\n'%int(ngoodsubs+1))
                ngoodsubs+=1
            else:
                print "WARNING: featfile not found: %s, was not added to *.fsf\n"%featfile, 
                
        if ngoodsubs==0:
            print "ERROR: No subjects with feat files found"
            sys.exit(-1)

        #Note: "feat won't run if zero feat_files are added to this fsf."
        outfile.write('set fmri(npts) %d\n'%ngoodsubs) # number of runs
        outfile.write('set fmri(multiple) %d\n'%ngoodsubs) # number of runs

        outfile.close()
    
    """
    for f in fsfnames:
        print f
    """
    return fsfnames

if __name__ == '__main__':
    main()