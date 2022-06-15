#!/usr/bin/env python
""" mk_fsf.py - make first-level FSF model
- this version has support for BBR and also introduces a new set of command line options

USAGE: mk_level1_fsf_bbr.py <studyid> <sub> <taskname> <runname> <smoothing - mm> <use_inplane> <basedir> <nonlinear>

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

#Modified by Akram Bakkour to work on yeti 06/2016
#Modified by Alice Xue to work with BIDS-like directory structure 05/2018

# create fsf file for arbitrary design

import argparse
from collections import OrderedDict
import inspect
import json
import numpy as N
import os
import subprocess as sub
import sys

import nifti_utils
from openfmri_utils import *

def parse_command_line(argv):
    parser = argparse.ArgumentParser(argv, description='setup_subject')

    parser.add_argument('--studyid', dest='studyid',
        required=True,help='Study ID')
    parser.add_argument('--sub', dest='subid',
        required=True,help='subject identifier (not including prefix "sub-")')
    parser.add_argument('--taskname', dest='taskname',
       required=True,help='Task name')
    parser.add_argument('--runname', dest='runname',
        required=True,help='Run name')
    parser.add_argument('--basedir', dest='basedir',
        required=True,help='Base directory (above studyid directory)')
    parser.add_argument('--smoothing', dest='smoothing',type=int,
        default=0,help='Smoothing (mm FWHM)')
    parser.add_argument('--use_inplane', dest='use_inplane', type=int,
        default=0,help='Use inplane image')
    parser.add_argument('--nonlinear', dest='nonlinear', action='store_true',
        default=False,help='Use nonlinear registration')
    parser.add_argument('--nohpf', dest='hpf', action='store_false',
        default=True,help='Turn off high pass filtering')
    parser.add_argument('--nowhiten', dest='whiten', action='store_false',
        default=True,help='Turn off prewhitening')
    parser.add_argument('--noconfound', dest='confound', action='store_false',
        default=True,help='Omit motion/confound modeling')
    parser.add_argument('-m', '--modelname', dest='modelname',
        required=True,help='Model name')
    parser.add_argument('--anatimg', dest='anatimg',
        default='',help='Anatomy image (should be _brain)')
    parser.add_argument('--doreg', dest='doreg', action='store_true',
        default=False,help='Do registration')
    parser.add_argument('--spacetag', dest='spacetag',
        default='',help='Space tag for preprocessed data')
    parser.add_argument('--sesname', dest='sesname',
        default='',help='Name of session (not including "ses-")')
    parser.add_argument('--usebrainmask', dest='usebrainmask', action='store_true',
        default=False,help='Apply custom brain mask to preproc file using fslmaths mas when calling feat')
    parser.add_argument('--callfeat', dest='callfeat', action='store_true',
        default=False,help='Call fsl\'s feat on the .fsf file that is created')
    
    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args=parse_command_line(argv)
    print(args)
      
    mk_level1_fsf_bbr(args)


# a: Namespace object, output of parser_command_line
def mk_level1_fsf_bbr(a):

    # attributes in a:
    #studyid,subid,taskname,runname,smoothing,use_inplane,basedir,nonlinear,modelname,anatimg,confound,hpf,whiten,doreg,sesname,spacetag,usebrainmask,callfeat

    _thisDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    tasknum = 1

    # Create the folders that are needed
    projdir=os.path.join(a.basedir,a.studyid)
    subid='sub-%s'%(a.subid)
    subid_ses=subid
    if a.sesname!="":
        subid_ses+="_ses-%s"%(a.sesname)
    fmriprep_subdir=os.path.join(a.basedir,'%s/fmriprep/%s'%(a.studyid,subid))
    if a.sesname!="":
        fmriprep_subdir=os.path.join(fmriprep_subdir,'ses-%s'%(a.sesname))
    if not os.path.exists(fmriprep_subdir):
        print("ERROR: No fmriprep folder found for this subject. Checked %s"%(fmriprep_subdir))
        sys.exit(-1)
    model_subdir='%s/model/level1/model-%s/%s'%(os.path.join(a.basedir,a.studyid),a.modelname,subid)
    if a.sesname!="":
        model_subdir=os.path.join(model_subdir,'ses-%s'%(a.sesname))
    model_subdir=os.path.join(model_subdir,'task-%s_run-%s'%(a.taskname,a.runname))
    if not os.path.exists(model_subdir):
        os.makedirs(model_subdir)


    ## Get anat preprocessed data from fmriprep
    # anat dir directly under subject folder
    anatdircontent = []
    anatdir = os.path.join(os.path.join(a.basedir,'%s/fmriprep/%s'%(a.studyid,subid)),'anat')
    if os.path.exists(anatdir):
        anatdircontent = os.listdir(anatdir)

    # anat dir under session folder
    sesanatdircontent=[]
    if a.sesname!="":
        sesanatdir = os.path.join(os.path.join(a.basedir,'%s/fmriprep/%s/ses-%s'%(a.studyid,subid,a.sesname)),'anat')
        if os.path.exists(sesanatdir):
            sesanatdircontent = os.listdir(sesanatdir)

    anat_preproc_files = []

    # check directory directly under subject folder
    anathead='%s'%(subid)
    anattail='.nii.gz'
    for fname in anatdircontent:
        if fname.startswith(anathead) and ('space' in fname) and ('preproc' in fname) and ('T1w' in fname) and fname.endswith(anattail):
            anat_preproc_files.append(os.path.join(anatdir,fname))

    # check directory under session folder
    if a.sesname!="":
        anathead='%s'%(subid)
        sesanathead='%s_ses-%s'%(subid,a.sesname)
        anattail='.nii.gz'
        for fname in sesanatdircontent:
            if (fname.startswith(anathead) or fname.startswith(sesanathead)) and ('space' in fname) and ('preproc' in fname) and ('T1w' in fname) and fname.endswith(anattail):
                anat_preproc_files.append(os.path.join(sesanatdir,fname))

    # find initial_high_res_file in anat_preproc_files found above
    if len(anat_preproc_files) == 1:
        initial_highres_file = anat_preproc_files[0]
    elif len(anat_preproc_files) == 0:
        if a.sesname=="":
            print("ERROR: Could not find preprocessed anat file in %s. Make sure this directory points to the output of fmriprep."%(anatdir))
            print("\tNOTE: Looked for 'T1w', 'space', 'preproc' in file name.")
        else:
            print("ERROR: Could not find preprocessed anat file in %s or %s. Make sure this directory points to the output of fmriprep."%(anatdir,sesanatdir))
            print("\tNOTE: Looked for 'T1w', 'space', 'preproc' in file name.")
        sys.exit(-1)
    else:
        print(fmriprep_subdir+'/'+anathead+a.spacetag+anattail)
        if a.spacetag!='' and os.path.exists(fmriprep_subdir+'/anat/'+anathead+a.spacetag+anattail):
            initial_highres_file = anathead+a.spacetag+anattail
        else:
            print("ERROR: Found multiple preprocessed anat files. Please make sure the directory is structured correctly.")
            print("Files found:", anat_preproc_files)
            print("If the files listed above are in the same directory, specify the space tag you want to use in the arguments.")
            sys.exit(-1)

    # Get func preprocessed data from fmriprep
    funcdir = os.path.join(fmriprep_subdir,'func')
    funcdircontent = os.listdir(funcdir)
    func_preproc_files = []
    funchead='%s_task-%s_run-%s'%(subid_ses,a.taskname,a.runname)
    functail='.nii.gz'
    fmriprep_brainmask=""
    fslmaths_preproc_brainmask=""
    for fname in funcdircontent:
        if fname.startswith(funchead) and ('preproc' in fname) and ('bold' in fname) and ('brain' not in fname) and fname.endswith(functail):
            func_preproc_files.append(fname)
        if a.usebrainmask: # if creating custom brain mask using fslmaths, get the brain mask file from the func dir
            if fname.startswith(funchead) and fname.endswith('_brainmask.nii.gz'):
                fmriprep_brainmask=fname
                i=fname.find('_brainmask.nii.gz')
                fslmaths_preproc_brainmask=fname[:i]+'_preproc_brain.nii.gz'
            # for post fmriprep 1.4.0
        elif fname.startswith(funchead) and fname.endswith('-brain_mask.nii.gz'):
            fmriprep_brainmask=fname
        i=fname.find('-brain_mask.nii.gz')
        fslmaths_preproc_brainmask=fname[:i]+'-preproc_brain.nii.gz'
    # find initial_high_res_file in func_preproc_files found above
    if len(func_preproc_files) == 1:
        func_preproc_file = func_preproc_files[0]
    elif len(func_preproc_files) == 0:
        print("ERROR: Could not find preprocessed functional file in %s. Make sure this directory points to the output of fmriprep."%(funcdir))
        print("\tNOTE: Looked for 'preproc' and 'bold' in the file name. (Excluded files with 'brain' in file name).")
        sys.exit(-1)
    else:
        if a.spacetag!='' and os.path.exists(fmriprep_subdir+'/func/'+funchead+a.spacetag+functail):
            func_preproc_file = funchead+a.spacetag+functail
        else:
            print("ERROR: Found multiple preprocessed func files here: %s. Please specify the label in the arguments."%(funcdir))
            print(func_preproc_files)
            sys.exit(-1)
    if a.usebrainmask and fslmaths_preproc_brainmask=="":
        print("ERROR: usebrainmask is true, but brain mask was not found in %s"%(funcdir))
        sys.exit(-1)

    if "MNI152NLin2009cAsym" not in func_preproc_file and not a.doreg:
        print("\nWARNING: It appears that your preprocessed functional file %s is not in MNI152NLin2009cAsym space. You may want to do registration."%(func_preproc_file))


    # not tested yet
    print('PROCESSING:',fmriprep_subdir)
    anatimg=a.anatimg
    if anatimg=='':
        anatimg=os.path.join(fmriprep_subdir,'anatomy/highres001_brain')
    
    # read the conditions_key file 
    # if it's a json file
    cond_key_json = os.path.join(a.basedir,a.studyid,'model/level1/model-%s/condition_key.json'%a.modelname)
    # if it's a text file
    cond_key_txt = os.path.join(a.basedir,a.studyid,'model/level1/model-%s/condition_key.txt'%a.modelname)
    if os.path.exists(cond_key_json):
        conddict = json.load(open(cond_key_json), object_pairs_hook=OrderedDict) # keep the order of the keys as they were in the json file 
        conddict_keys=[]
        if a.taskname in conddict.keys():
            # set conddict to the dictionary for this task where 
                # the EV names are the keys
                # and the names of the conditions are the values
            conddict = conddict[a.taskname] 
            for key,value in conddict.items():
                conddict_keys.append(key)
        else:
            print("ERROR: Task name %s was not found in condition_key.json. Make sure the JSON file is formatted correctly"%(a.taskname))
            sys.exit(-1)
        ev_keys = conddict_keys
        ev_files=[]
        conditions=[]
        # get the names of the EV files and the names of the conditions
        for ev in ev_keys:
            ev_files.append('%s_task-%s_run-%s_ev-%03d'%(subid_ses,a.taskname,a.runname,int(ev)))
            conditions.append(conddict[ev])  
        print("found conditions:",conditions)
    elif os.path.exists(cond_key_txt):
        cond_key=load_condkey(cond_key_txt)

        conditions=cond_key[a.taskname].values()
        print('found conditions:',conditions)
    else:
        print("ERROR: Could not find condition key in %s"%(os.path.join(a.basedir,a.studyid,'model/level1/model-%s'%a.modelname)))
        sys.exit(-1)

    # not tested yet
    # check for orthogonalization file
    orth={}
    orthfile=os.path.join(a.basedir,a.studyid,'model/level1/model-%s/orthogonalize.txt'%a.modelname)
    #orthfile=os.path.join(a.basedir,a.studyid,'models/model-%s/orthogonalize.txt'%a.modelname)
    if os.path.exists(orthfile):
        f=open(orthfile)
        for l in f.readlines():
            orth_tasknum=int(l.split()[0].replace('task',''))
            if orth_tasknum==tasknum:
                orth[int(l.split()[1])]=int(l.split()[2])
        f.close()
    else:
        print('no orthogonalization found')
        
    # not tested yet
    # check for QA dir
    #qadir='%s/BOLD/task%03d_run%03d/QA'%(fmriprep_subdir,tasknum,a.runname)
    qadir='%s/QA'%(fmriprep_subdir)


    # Get task contrasts
    print('loading contrasts')
    # if it's a json file
    contrastsfile_json=os.path.join(a.basedir,a.studyid,'model/level1/model-%s/task_contrasts.json'%a.modelname)
    # if it's a txt file
    contrastsfile_txt=os.path.join(a.basedir,a.studyid,'model/level1/model-%s/task_contrasts.txt'%a.modelname)
    if os.path.exists(contrastsfile_json):
        contrasts_all = json.load(open(contrastsfile_json), object_pairs_hook=OrderedDict)
        contrasts_keys=[]
        for contrast,value in contrasts_all.items():
            contrasts_keys.append(contrast)
    elif os.path.exists(contrastsfile_txt):
        contrasts_all=load_contrasts(contrastsfile)
    else:
        print("WARNING: Could not find task_contrasts file in %s"%(os.path.join(a.basedir,a.studyid,'model/level1/model-%s'%a.modelname)))
        contrasts_all={}
    print('added contrasts:',contrasts_all)

    contrasts=[]
    if a.taskname in contrasts_all:
        contrasts=contrasts_all[a.taskname]
    elif os.path.exists(contrastsfile_json) or os.path.exists(contrastsfile_txt):
        print("ERROR: Could not find task name %s in contrasts. Make sure the file is formatted correctly.")
        sys.exit(-1)

    # Find Repetition Time - from header of preprocessed func file
    tr=nifti_utils.get_tr('%s/func/%s'%(fmriprep_subdir,func_preproc_file))
    
    # Get fsf template with default values
    stubfilename=os.path.join(_thisDir,'design_level1_fsl5.stub')
    customstubfilename=os.path.join(a.basedir,a.studyid,'model/level1/model-%s/design_level1_custom.stub'%a.modelname)
    # Name of fsf file to create
    outfilename='%s/%s_task-%s_run-%s.fsf'%(model_subdir,subid_ses,a.taskname,a.runname)
    print('outfilename: %s\n'%outfilename)
    outfile=open(outfilename,'w')
    outfile.write('# Automatically generated by mk_fsf.py\n')

    # Get settings from custom stub file, store in customsettings dictionary 
    # in customsettings, key is the setting ('fmri(mc)' for example) and the value of the setting is the value
    customsettings={}
    if os.path.exists(customstubfilename):
        print('Found custom fsf stub')
        customstubfile=open(customstubfilename,'r')
        for l in customstubfile:
            llist=l.split(' ')
            if len(l)>3 and llist[0]=='set':
                setting=llist[1]
                value=llist[2]
                customsettings[setting]=value
        customstubfile.close()

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

    # figure out how many timepoints there are 
    p = sub.Popen(['fslinfo', '%s/func/%s'%(fmriprep_subdir,func_preproc_file)], stdout=sub.PIPE, stderr=sub.PIPE,
                  encoding='utf8')
    output, errors = p.communicate()

    ntp=int(output.split('\n')[4].split()[1])

    #img=nibabel.load('%s/BOLD/task%03d_run%03d/bold_mcf_brain.nii.gz'%(fmriprep_subdir,tasknum,a.runname))
    #h=img.get_header()
    #ntp=h.get_data_shape()[3]
    
    outfile.write('\n\n### AUTOMATICALLY GENERATED PART###\n\n')
    # now add custom lines
    outfile.write( 'set fmri(regstandard_nonlinear_yn) %d\n'%a.nonlinear)

    # not tested - used to be read from scan_key.txt 
    # Delete volumes
    nskip=0
    outfile.write('set fmri(ndelete) %d\n'%nskip)

    # do or don't do registration
    outfile.write('set fmri(reg_yn) %d\n'%a.doreg)
    outfile.write('set fmri(reginitial_highres_yn) %d\n'%a.doreg)
    outfile.write('set fmri(reghighres_yn) %d\n'%a.doreg)
    outfile.write('set fmri(regstandard_yn) %d\n'%a.doreg)

    # look for standard brain fsl provides
    env = os.environ.copy()
    FSLDIR='/usr/local/fsl'
    if 'FSLDIR' in env.keys():
        FSLDIR=env["FSLDIR"]
    elif 'FSL_DIR' in env.keys():
        FSLDIR=env["FSL_DIR"]
    regstandard=os.path.join(FSLDIR,'data/standard/MNI152_T1_2mm_brain')
    outfile.write('set fmri(regstandard) "%s"\n'%regstandard)

    outfile.write('set fmri(outputdir) "%s/%s_task-%s_run-%s.feat"\n'%(model_subdir,subid_ses,a.taskname,a.runname))
    if not a.usebrainmask:
        outfile.write('set feat_files(1) "%s"\n'%(os.path.join(funcdir,func_preproc_file)))
    else:
        outfile.write('set feat_files(1) "%s"\n'%(os.path.join(funcdir,fslmaths_preproc_brainmask)))

    if a.use_inplane==1:
        outfile.write('set fmri(reginitial_highres_yn) 1\n')
        outfile.write('set initial_highres_files(1) "%s"\n'%(initial_highres_file))
    else:
        outfile.write('set fmri(reginitial_highres_yn) 0\n')

    if a.whiten:
        outfile.write('set fmri(prewhiten_yn) 1\n')
    else:
        outfile.write('set fmri(prewhiten_yn) 0\n')
       
    if a.hpf:
        outfile.write('set fmri(temphp_yn) 1\n')
    else:
        outfile.write('set fmri(temphp_yn) 0\n')

    outfile.write('set highres_files(1) "%s"\n'%anatimg)
    outfile.write('set fmri(npts) %d\n'%ntp)
    outfile.write('set fmri(tr) %0.2f\n'%tr)
    nevs=len(conditions)
    outfile.write('set fmri(evs_orig) %d\n'%nevs)
    outfile.write('set fmri(evs_real) %d\n'%(2*nevs))
    outfile.write('set fmri(smooth) %d\n'%a.smoothing)
    outfile.write('set fmri(ncon_orig) %d\n'%(len(conditions)+1+len(contrasts)))
    outfile.write('set fmri(ncon_real) %d\n'%(len(conditions)+1+len(contrasts)))

    # loop through EVs
    convals_real=N.zeros(nevs*2)
    convals_orig=N.zeros(nevs)
    empty_evs=[]

    # iterate through the EVs
    for ev in range(len(conditions)):
        outfile.write('\n\nset fmri(evtitle%d) "%s"\n'%(ev+1,conditions[ev]))

        ## get the full path of the EV file
        # if it's a json file
        if os.path.exists(cond_key_json):
            condfile='%s/onsets/%s'%(model_subdir,ev_files[ev])
            if os.path.exists(condfile+'.txt'):
                condfile+='.txt'
            elif os.path.exists(condfile+'.tsv'):
                condfile+='.tsv'
        else:
            condfile='%s/onsets/%s_task-%s_run-%s_ev-%03d.txt'%(model_subdir,subid_ses,a.taskname,a.runname,ev+1)
        # if the EV file exists
        if os.path.exists(condfile):
            outfile.write('set fmri(shape%d) 3\n'%(ev+1))
            outfile.write('set fmri(custom%d) "%s"\n'%(ev+1,condfile))
        # if the EV file is missing
        else:
             outfile.write('set fmri(shape%d) 10\n'%(ev+1))
             print('%s is missing, using empty EV'%condfile)
             empty_evs.append(ev+1)
             
        outfile.write('set fmri(convolve%d) 3\n'%(ev+1))
        outfile.write('set fmri(convolve_phase%d) 0\n'%(ev+1))
        outfile.write('set fmri(tempfilt_yn%d) 1\n'%(ev+1))
        outfile.write('set fmri(deriv_yn%d) 1\n'%(ev+1))

        # first write the orth flag for zero, which seems to be turned on whenever
        # anything is orthogonalized
        
        if ev+1 in orth:
                outfile.write('set fmri(ortho%d.0) 1\n'%int(ev+1))
        else:
                outfile.write('set fmri(ortho%d.0) 0\n'%int(ev+1))
        
        for evn in range(1,nevs+1):
            if ev+1 in orth:
                if orth[ev+1]==evn:
                    outfile.write('set fmri(ortho%d.%d) 1\n'%(ev+1,evn))
                else:
                    outfile.write('set fmri(ortho%d.%d) 0\n'%(ev+1,evn))
            else:
                outfile.write('set fmri(ortho%d.%d) 0\n'%(ev+1,evn))
        # make a T contrast for each EV
        outfile.write('set fmri(conpic_real.%d) 1\n'%(ev+1))
        outfile.write('set fmri(conpic_orig.%d) 1\n'%(ev+1))
        outfile.write('set fmri(conname_real.%d) "%s"\n'%(ev+1,conditions[ev]))
        outfile.write('set fmri(conname_orig.%d) "%s"\n'%(ev+1,conditions[ev]))
        for evt in range(nevs*2):
            outfile.write('set fmri(con_real%d.%d) %d\n'%(ev+1,evt+1,int(evt==(ev*2))))
            if (evt==(ev*2)):
                convals_real[evt]=1
        for evt in range(nevs):
            outfile.write('set fmri(con_orig%d.%d) %d\n'%(ev+1,evt+1,int(evt==ev)))
            if (evt==ev):
                convals_orig[evt]=1
                
    # to deal with missing EVs
    if len(empty_evs)>0:
        empty_ev_file=open('%s/onsets/%s_task-%s_run-%s_empty_evs.txt'%(model_subdir,subid_ses,a.taskname,a.runname),'w')
        for eev in empty_evs:
            empty_ev_file.write('%d\n'%eev)
        empty_ev_file.close()

    # make one additional contrast across all conditions
    outfile.write('set fmri(conpic_real.%d) 1\n'%(ev+2))
    outfile.write('set fmri(conname_real.%d) "all"\n'%(ev+2))
    outfile.write('set fmri(conname_orig.%d) "all"\n'%(ev+2))

    for evt in range(nevs*2):
        outfile.write('set fmri(con_real%d.%d) %d\n'%(ev+2,evt+1,convals_real[evt]))
    for evt in range(nevs):
        outfile.write('set fmri(con_orig%d.%d) %d\n'%(ev+2,evt+1,convals_orig[evt]))

    # add custom contrasts
    if len(contrasts)>0:
        print(contrasts)
        contrastctr=ev+3;
        for c in contrasts.keys():
            
            outfile.write('set fmri(conpic_real.%d) 1\n'%contrastctr)
            outfile.write('set fmri(conname_real.%d) "%s"\n'%(contrastctr,c))
            outfile.write('set fmri(conname_orig.%d) "%s"\n'%(contrastctr,c))
            cveclen=len(contrasts[c])
            con_real_ctr=1
            for evt in range(nevs):
                outfile.write('set fmri(con_real%d.%d) %s\n'%(contrastctr,con_real_ctr,contrasts[c][evt]))
                outfile.write('set fmri(con_real%d.%d) 0\n'%(contrastctr,con_real_ctr+1))
                con_real_ctr+=2
                    
            for evt in range(nevs):
                if evt<cveclen:
                    outfile.write('set fmri(con_orig%d.%d) %s\n'%(contrastctr,evt+1,contrasts[c][evt]))
                else:
                    outfile.write('set fmri(con_orig%d.%d) 0\n'%(contrastctr,evt+1))

            contrastctr+=1
    
    # Add confound EVs text file
    confoundfile='%s/onsets/%s_task-%s_run-%s_ev-confounds.tsv'%(model_subdir,subid_ses,a.taskname,a.runname)
    if not os.path.exists(confoundfile):
        confoundfile='%s/onsets/%s_task-%s_run-%s_ev-confounds.txt'%(model_subdir,subid_ses,a.taskname,a.runname)
    if os.path.exists(confoundfile) and a.confound:
        outfile.write('set fmri(confoundevs) 1\n')
        outfile.write('set confoundev_files(1) "%s"\n'%confoundfile)
    else:
        print("No confounds file found")
        outfile.write('set fmri(confoundevs) 0\n')
        
    outfile.close()

    if a.callfeat:
        if a.usebrainmask:
            fslmathsargs = ["fslmaths",os.path.join(funcdir,func_preproc_file),"-mas",os.path.join(funcdir,fmriprep_brainmask),os.path.join(funcdir,fslmaths_preproc_brainmask)]
            print("Applying fslmath's mas, creating the following file: %s"%(fslmaths_preproc_brainmask))
            sub.call(fslmathsargs)
        featargs = ["feat",outfilename]
        print("Calling", ' '.join(featargs))
        sub.call(featargs)

    return outfilename

if __name__ == '__main__':
    main()
