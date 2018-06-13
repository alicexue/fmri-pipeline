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
import numpy as N
import sys
import os
import subprocess as sub
import json
from collections import OrderedDict
import argparse
from openfmri_utils import *
from directory_struct_utils import *

def parse_command_line(argv):
    parser = argparse.ArgumentParser(argv, description='setup_task')
    #parser.add_argument('integers', metavar='N', type=int, nargs='+',help='an integer for the accumulator')
    # set up boolean flags

    parser.add_argument('--studyid', dest='studyid',
        required=True,help='Study ID')
    parser.add_argument('--subs', dest='subids', nargs='+',
        default=[],help='subject identifiers (not including prefix "sub-")')
    parser.add_argument('--taskname', dest='taskname',
        required=True,help='Task name')
    parser.add_argument('--basedir', dest='basedir',
        required=True,help='Base directory (above studyid directory)')
    parser.add_argument('--modelnum', dest='modelnum',type=int,
        default=1,help='Model number')
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
    modelnum=args.modelnum
    sesname=args.sesname
      
    mk_level3_fsf(studyid,subids,taskname,basedir,modelnum,sesname)


def mk_level3_fsf(studyid,subids,taskname,basedir,modelnum,sesname):
    print subids
    _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
    studydir=os.path.join(basedir,studyid)

    #groupdir='%s%s/group/model%03d'%(studydir,taskname,modelnum)
    groupdir='%s/model/level3/model%03d'%(studydir,modelnum)
    if not os.path.exists(groupdir):
        os.makedirs(groupdir)

    #modeldir='%s%s/group/model%03d/task%03d'%(studydir,taskname,modelnum,taskname)
    modeldir='%s/model/level3/model%03d'%(studydir,modelnum)
    if sesname!='':
        modeldir+='/ses-%s'%(sesname)
    modeldir=os.path.join(modeldir,'task-%s'%taskname)
    if not os.path.exists(modeldir):
        os.makedirs(modeldir)

    # read the conditions_key file
    cond_key_json = os.path.join(basedir,studyid,'model/level1/model%03d/condition_key.json'%modelnum)
    # if it's a text file
    cond_key_txt = os.path.join(basedir,studyid,'model/level1/model%03d/condition_key.txt'%modelnum)
    if os.path.exists(cond_key_json):
        cond_key = json.load(open(cond_key_json), object_pairs_hook=OrderedDict)
        if taskname in cond_key.keys():
            cond_key = cond_key[taskname]
        else:
            print "ERROR: Task name was not found in JSON file %s. Make sure the JSON file is formatted correctly"%(cond_key_json)
            sys.exit(-1)
        nconditions = len(cond_key.keys())
    elif os.path.exists(cond_key_txt):
        cond_key=load_condkey(cond_key_txt)
        conditions=cond_key[taskname].values()
        cond_key = cond_key[taskname]
    else:
        print "ERROR: Could not find condition key in %s"%(os.path.join(basedir,studyid,'model/level1/model%03d'%modelnum))
        sys.exit(-1)

    contrastsfile_json=os.path.join(basedir,studyid,'model/level1/model%03d/task_contrasts.json'%modelnum)
    contrastsfile_txt=os.path.join(basedir,studyid,'model/level1/model%03d/task_contrasts.txt'%modelnum)
    if os.path.exists(contrastsfile_json):
        all_addl_contrasts = json.load(open(contrastsfile_json), object_pairs_hook=OrderedDict)
        all_addl_contrasts = dict(all_addl_contrasts)
        for contrast in all_addl_contrasts:
            all_addl_contrasts[contrast] = dict(all_addl_contrasts[contrast])
    elif os.path.exists(contrastsfile_txt):
        all_addl_contrasts=load_contrasts(contrastsfile)
    else:
        print "WARNING: Could not find task_contrasts file in %s"%(os.path.join(studydir,studyid,'model/level1/model%03d'%modelnum))
        all_addl_contrasts={}
    if all_addl_contrasts.has_key(taskname):
        addl_contrasts=all_addl_contrasts[taskname]
        n_addl_contrasts=len(addl_contrasts)
    else:
        n_addl_contrasts=0

    # figure out the number of copes
    ncopes=nconditions+1+n_addl_contrasts

    stubfilename=os.path.join(_thisDir,'design_level3.stub')
    fsfnames=[]
    for copenum in range(1,ncopes+1):
        if sesname!='':
            outfilename='%s/ses-%s_task-%s_cope-%03d.fsf'%(modeldir,sesname,taskname,copenum)
        else:
            outfilename='%s/task-%s_cope-%03d.fsf'%(modeldir,taskname,copenum)
        fsfnames.append(outfilename)
 #       print('%s\n'%outfilename)
        outfile=open(outfilename,'w')
        outfile.write('# Automatically generated by mk_fsf.py\n')

        # first get common lines from stub file
        stubfile=open(stubfilename,'r')
        for l in stubfile:
            outfile.write(l)

        stubfile.close()

        # now add custom lines

        outfile.write('\n\n### AUTOMATICALLY GENERATED PART###\n\n')

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
        if len(subids)==0:
            sublist=get_all_subs(studydir)
        else:
            sublist=subids
        
        for sub in sublist:
            subid_ses="sub-"+sub
            subid_ses_dir="sub-"+sub
            if sesname!="":
                subid_ses+="_ses-%s"%(sesname)
                subid_ses_dir+="/ses-%s"%(sesname)
            featfile=os.path.join(studydir,'model/level2/model%03d/%s/task-%s/%s_task-%s.gfeat/cope%d.feat'%(modelnum,subid_ses_dir,taskname,subid_ses,taskname,copenum))
            if os.path.exists(featfile):
                outfile.write('set feat_files(%d) "%s"\n'%(ngoodsubs+1,featfile))
                outfile.write('set fmri(evg%d.1) 1\n'%int(ngoodsubs+1))
                outfile.write('set fmri(groupmem.%d) 1\n'%int(ngoodsubs+1))
                ngoodsubs+=1
            else:
                print "WARNING: featfile not found: %s, was not added to *.fsf"%featfile, 
                
        #Note: "feat won't run if feat_files are not added to this fsf."
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