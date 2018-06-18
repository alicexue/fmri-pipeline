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
import numpy as N
import sys
import os
import subprocess as sub
from openfmri_utils import *
import argparse
import json
from collections import OrderedDict
#import nibabel

def parse_command_line(argv):
    parser = argparse.ArgumentParser(argv, description='setup_subject')
    #parser.add_argument('integers', metavar='N', type=int, nargs='+',help='an integer for the accumulator')
    # set up boolean flags


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
        default=False,help='Use nonlinear regristration')
    parser.add_argument('--nohpf', dest='hpf', action='store_false',
        default=True,help='Turn off high pass filtering')
    parser.add_argument('--nowhiten', dest='whiten', action='store_false',
        default=True,help='Turn off prewhitening')
    parser.add_argument('--noconfound', dest='confound', action='store_false',
        default=True,help='Omit motion/confound modeling')
    parser.add_argument('--modelnum', dest='modelnum',type=int,
        default=1,help='Model number')
    parser.add_argument('--anatimg', dest='anatimg',
        default='',help='Anatomy image (should be _brain)')
    parser.add_argument('--doreg', dest='doreg', action='store_true',
        default=False,help='Do registration')
    parser.add_argument('--spacetag', dest='spacetag',
        default='',help='Space tag for preprocessed data')
    parser.add_argument('--altBETmask', dest='altBETmask', action='store_true',
        default=False,help='Use brainmask from fmriprep')
    parser.add_argument('--sesname', dest='sesname',
        default='',help='Name of session (not including "ses-")')
    parser.add_argument('--callfeat', dest='callfeat', action='store_true',
        default=False,help='Call fsl\'s feat on the .fsf file that is created')
    
    args = parser.parse_args(argv)
    return args

# create as a function that will be called by mk_all_fsf.py
# just set these for testing
## studyid='ds103'
## runname=1
## smoothing=6
## use_inplane=0
## nonlinear=1

def main(argv=None):
    args=parse_command_line(argv)
    print args
    
    studyid=args.studyid
    subid=args.subid
    taskname=args.taskname
    runname=args.runname
    smoothing=args.smoothing
    use_inplane=args.use_inplane
    basedir=args.basedir
    nonlinear=args.nonlinear
    modelnum=args.modelnum
    anatimg=args.anatimg
    confound=args.confound
    hpf = args.hpf
    whiten=args.whiten
    doreg=args.doreg
    sesname=args.sesname
    spacetag=args.spacetag
    altBETmask=args.altBETmask
    callfeat=args.callfeat
      
    mk_level1_fsf_bbr(studyid,subid,taskname,runname,smoothing,use_inplane,basedir,nonlinear,modelnum,anatimg,confound,hpf,whiten,doreg,sesname,spacetag,altBETmask,callfeat)

def mk_level1_fsf_bbr(studyid,subid,taskname,runname,smoothing,use_inplane,basedir,nonlinear=1,modelnum=1,anatimg='',confound=True,hpf=True,whiten=True,doreg=False,sesname='',spacetag='',altBETmask=False,callfeat=False):
    _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
    tasknum = 1

    ###
    projdir=os.path.join(basedir,studyid)
    subid='sub-%s'%(subid)
    subid_ses=subid
    if sesname!="":
        subid_ses+="_ses-%s"%(sesname)
    fmriprep_subdir=os.path.join(basedir,'%s/fmriprep/%s'%(studyid,subid))
    if sesname!="":
        fmriprep_subdir=os.path.join(fmriprep_subdir,'ses-%s'%(sesname))
    if not os.path.exists(fmriprep_subdir):
        print "ERROR: No fmriprep folder found for this subject. Checked %s"%(fmriprep_subdir)
        sys.exit(-1)
    model_subdir='%s/model/level1/model%03d/%s'%(os.path.join(basedir,studyid),modelnum,subid)
    if sesname!="":
        model_subdir=os.path.join(model_subdir,'ses-%s'%(sesname))
    model_subdir=os.path.join(model_subdir,'task-%s_run-%s'%(taskname,runname))
    if not os.path.exists(model_subdir):
        os.makedirs(model_subdir)
    ###


    ## Get anat preprocessed data from fmriprep

    # anat dir directly under subject folder
    anatdircontent = []
    anatdir = os.path.join(os.path.join(basedir,'%s/fmriprep/%s'%(studyid,subid)),'anat')
    if os.path.exists(anatdir):
        anatdircontent = os.listdir(anatdir)

    # anat dir under session folder
    sesanatdircontent=[]
    if sesname!="":
        sesanatdir = os.path.join(os.path.join(basedir,'%s/fmriprep/%s/ses-%s'%(studyid,subid,sesname)),'anat')
        if os.path.exists(sesanatdir):
            sesanatdircontent = os.listdir(sesanatdir)

    anat_preproc_files = []

    # check directory directly under subject folder
    anathead='%s_T1w_space-'%(subid)
    anattail='_preproc.nii.gz'
    for fname in anatdircontent:
        if fname.startswith(anathead) and fname.endswith(anattail):
            anat_preproc_files.append(os.path.join(anatdir,fname))

    # check directory under session folder
    if sesname!="":
        anathead='%s_T1w_space-'%(subid)
        sesanathead='%s_ses-%s_T1w_space-'%(subid,sesname)
        anattail='_preproc.nii.gz'
        for fname in sesanatdircontent:
            if (fname.startswith(anathead) or fname.startswith(sesanathead)) and fname.endswith(anattail):
                anat_preproc_files.append(os.path.join(sesanatdir,fname))

    if len(anat_preproc_files) == 1:
        initial_highres_file = anat_preproc_files[0]
    elif len(anat_preproc_files) == 0:
        print "ERROR: Could not find preprocessed anat file in %s or %s. Make sure this directory points to the output of fmriprep."%(anatdir,sesanatdir)
        sys.exit(-1)
    else:
        print fmriprep_subdir+'/'+anathead+spacetag+anattail
        if spacetag!='' and os.path.exists(fmriprep_subdir+'/anat/'+anathead+spacetag+anattail):
            initial_highres_file = anathead+spacetag+anattail
        else:
            print "ERROR: Found multiple preprocessed anat files. Please make sure the directory is structured correctly."
            print "Files found:", anat_preproc_files
            print "If the files listed above are in the same directory, specify the space tag you want to use in the arguments."
            sys.exit(-1)

    # Get func preprocessed data from fmriprep
    funcdir = os.path.join(fmriprep_subdir,'func')
    funcdircontent = os.listdir(funcdir)
    func_preproc_files = []
    funchead='%s_task-%s_run-%s_bold_space-'%(subid_ses,taskname,runname)
    functail='_preproc.nii.gz'
    fmriprep_brainmask=""
    for fname in funcdircontent:
        if fname.startswith(funchead) and fname.endswith(functail):
            func_preproc_files.append(fname)
        if altBETmask:
            if fname.startswith(funchead) and fname.endswith('_brainmask.nii.gz'):
                fmriprep_brainmask=fname
    if len(func_preproc_files) == 1:
        func_preproc_file = func_preproc_files[0]
    elif len(func_preproc_files) == 0:
        print "ERROR: Could not find preprocessed functional file in %s. Make sure this directory points to the output of fmriprep."%(funcdir)
        sys.exit(-1)
    else:
        if spacetag!='' and os.path.exists(fmriprep_subdir+'/func/'+funchead+spacetag+functail):
            func_preproc_file = funchead+spacetag+functail
        else:
            print "ERROR: Found multiple preprocessed func files here: %s. Please specify the label in the arguments."%s(funcdir)
            print func_preproc_files
            sys.exit(-1)


    if "MNI152NLin2009cAsym" not in func_preproc_file and not doreg:
        print "\nWARNING: It appears that your preprocessed functional file %s is not in MNI152NLin2009cAsym space. You may want to do registration."%(func_preproc_file)

    ###

    print 'PROCESSING:',fmriprep_subdir
    if anatimg=='':
        anatimg=os.path.join(fmriprep_subdir,'anatomy/highres001_brain')
    
    # read the conditions_key file
    cond_key_json = os.path.join(basedir,studyid,'model/level1/model%03d/condition_key.json'%modelnum)
    # if it's a text file
    cond_key_txt = os.path.join(basedir,studyid,'model/level1/model%03d/condition_key.txt'%modelnum)
    if os.path.exists(cond_key_json):
        conddict = json.load(open(cond_key_json), object_pairs_hook=OrderedDict)
        if taskname in conddict.keys():
            conddict = conddict[taskname]
        else:
            print "ERROR: Task name was not found in JSON file. Make sure the JSON file is formatted correctly"
            sys.exit(-1)
        ev_keys = conddict.keys()
        list.sort(ev_keys)
        ev_files=[]
        conditions=[]
        for ev in ev_keys:
            ev_files.append('%s_task-%s_run-%s_ev-%03d'%(subid_ses,taskname,runname,int(ev)))
            conditions.append(conddict[ev])  
        print "found conditions:",conditions
    elif os.path.exists(cond_key_txt):
        cond_key=load_condkey(cond_key_txt)

        conditions=cond_key[taskname].values()
        print 'found conditions:',conditions
    else:
        print "ERROR: Could not find condition key in %s"%(os.path.join(basedir,studyid,'model/level1/model%03d'%modelnum))
        sys.exit(-1)

    # check for orthogonalization file
    orth={}
    orthfile=os.path.join(basedir,studyid,'model/level1/model%03d/orthogonalize.txt'%modelnum)
    #orthfile=os.path.join(basedir,studyid,'models/model%03d/orthogonalize.txt'%modelnum)
    if os.path.exists(orthfile):
        f=open(orthfile)
        for l in f.readlines():
            orth_tasknum=int(l.split()[0].replace('task',''))
            if orth_tasknum==tasknum:
                orth[int(l.split()[1])]=int(l.split()[2])
        f.close()
    else:
        print 'no orthogonalization found'
        
    # check for QA dir
    #qadir='%s/BOLD/task%03d_run%03d/QA'%(fmriprep_subdir,tasknum,runname)
    qadir='%s/QA'%(fmriprep_subdir)


    print 'loading contrasts'
    contrastsfile_json=os.path.join(basedir,studyid,'model/level1/model%03d/task_contrasts.json'%modelnum)
    contrastsfile_txt=os.path.join(basedir,studyid,'model/level1/model%03d/task_contrasts.txt'%modelnum)
    if os.path.exists(contrastsfile_json):
        contrasts_all = json.load(open(contrastsfile_json), object_pairs_hook=OrderedDict)
        contrasts_all = dict(contrasts_all)
        for contrast in contrasts_all:
            contrasts_all[contrast] = dict(contrasts_all[contrast])
    elif os.path.exists(contrastsfile_txt):
        contrasts_all=load_contrasts(contrastsfile)
    else:
        print "WARNING: Could not find task_contrasts file in %s"%(os.path.join(basedir,studyid,'model/level1/model%03d'%modelnum))
        contrasts_all={}
    print 'added contrasts:',contrasts_all

    contrasts=[]
    if contrasts_all.has_key(taskname):
        contrasts=contrasts_all[taskname]
    elif os.path.exists(contrastsfile_json) or os.path.exists(contrastsfile_txt):
        print "ERROR: Could not find task name %s in contrasts. Make sure the file is formatted correctly."
        sys.exit(-1)


    # Find Repetition Time
    tr=None
    scan_key_path1=os.path.join(basedir,studyid,'raw','task-%s_bold.json'%(taskname))
    if os.path.exists(scan_key_path1):
        scan_key=json.load(open(scan_key_path1))
        if 'RepetitionTime' in scan_key:
            tr=scan_key['RepetitionTime']
        else:
            print "Could not find RepetitionTime key in %s"%scan_key_path1

    scan_key_path2=os.path.join(basedir,studyid,'raw',subid,'func','%s_task-%s_run-%sbold.json'%(subid,taskname,runname))
    if os.path.exists(scan_key_path2):
        scan_key=json.load(open(scan_key_path2))
        if 'RepetitionTime' in scan_key:
            tr=scan_key['RepetitionTime']
        else:
            print "Could not find RepetitionTime key in %s"%scan_key_path2

    if tr==None:
        print "ERROR: Could not find scan key. Looked here: %s and here: %s."%(scan_key_path1,scan_key_path2)
        sys.exit(-1)

    if scan_key.has_key('nskip'):
        nskip=int(scan_key['nskip'])
    else:
        nskip=0
        
    #stubfilename='/vega/psych/users/ab4096/scripts/design_level1_fsl5.stub'
    #stubfilename='/Users/alicexue/Documents/ShohamyLab/fsl_testing/design_level1_fsl5.stub'
    stubfilename=os.path.join(_thisDir,'design_level1_fsl5.stub')
    
    outfilename='%s/%s_task-%s_run-%s.fsf'%(model_subdir,subid_ses,taskname,runname)
    print('outfilename: %s\n'%outfilename)
    outfile=open(outfilename,'w')
    outfile.write('# Automatically generated by mk_fsf.py\n')

    # first get common lines from stub file
    stubfile=open(stubfilename,'r')
    for l in stubfile:
        outfile.write(l)

    stubfile.close()
    # figure out how many timepoints there are

    #p = sub.Popen(['fslinfo','%s/BOLD/task%03d_run%03d/bold_mcf_brain'%(fmriprep_subdir,tasknum,runname)],stdout=sub.PIPE,stderr=sub.PIPE)
    p = sub.Popen(['fslinfo','%s/func/%s'%(fmriprep_subdir,func_preproc_file)],stdout=sub.PIPE,stderr=sub.PIPE)
    output, errors = p.communicate()

    ntp=int(output.split('\n')[4].split()[1])

    #img=nibabel.load('%s/BOLD/task%03d_run%03d/bold_mcf_brain.nii.gz'%(fmriprep_subdir,tasknum,runname))
    #h=img.get_header()
    #ntp=h.get_data_shape()[3]
    
    outfile.write('\n\n### AUTOMATICALLY GENERATED PART###\n\n')
    # now add custom lines
    outfile.write( 'set fmri(regstandard_nonlinear_yn) %d\n'%nonlinear)
    # Delete volumes
    outfile.write('set fmri(ndelete) %d\n'%nskip)

    # do or don't do registration
    outfile.write('set fmri(reg_yn) %d\n'%doreg)
    outfile.write('set fmri(reginitial_highres_yn) %d\n'%doreg)
    outfile.write('set fmri(reghighres_yn) %d\n'%doreg)
    outfile.write('set fmri(regstandard_yn) %d\n'%doreg)

    # use alternative brain mask
    if altBETmask:
        outfile.write('set fmri(alternative_mask) "%s/func/%s"\n'%(fmriprep_subdir,fmriprep_brainmask))
    else:
        outfile.write('set fmri(alternative_mask) ""\n')

    env = os.environ.copy()
    FSLDIR='/usr/local/fsl'
    if 'FSLDIR' in env.keys():
        FSLDIR=env["FSLDIR"]
    elif 'FSL_DIR' in env.keys():
        FSLDIR=env["FSL_DIR"]
    regstandard=os.path.join(FSLDIR,'data/standard/MNI152_T1_2mm_brain')
    outfile.write('set fmri(regstandard) "%s"\n'%regstandard)

    outfile.write('set fmri(outputdir) "%s/%s_task-%s_run-%s.feat"\n'%(model_subdir,subid_ses,taskname,runname))
    #outfile.write('set feat_files(1) "%s/BOLD/task%03d_run%03d/bold_mcf_brain.nii.gz"\n'%(fmriprep_subdir,tasknum,runname))
    outfile.write('set feat_files(1) "%s"\n'%(os.path.join(funcdir,func_preproc_file)))

    if use_inplane==1:
        outfile.write('set fmri(reginitial_highres_yn) 1\n')
        #outfile.write('set initial_highres_files(1) "%s/anatomy/inplane001_brain.nii.gz"\n'%fmriprep_subdir)
        outfile.write('set initial_highres_files(1) "%s"\n'%(initial_highres_file))
    else:
        outfile.write('set fmri(reginitial_highres_yn) 0\n')

    if whiten:
        outfile.write('set fmri(prewhiten_yn) 1\n')
    else:
        outfile.write('set fmri(prewhiten_yn) 0\n')
       
    if hpf:
        outfile.write('set fmri(temphp_yn) 1\n')
    else:
        outfile.write('set fmri(temphp_yn) 0\n')

    outfile.write('set highres_files(1) "%s"\n'%anatimg)
    outfile.write('set fmri(npts) %d\n'%ntp)
    outfile.write('set fmri(tr) %0.2f\n'%tr)
    nevs=len(conditions)
    outfile.write('set fmri(evs_orig) %d\n'%nevs)
    outfile.write('set fmri(evs_real) %d\n'%(2*nevs))
    outfile.write('set fmri(smooth) %d\n'%smoothing)
    outfile.write('set fmri(ncon_orig) %d\n'%(len(conditions)+1+len(contrasts)))
    outfile.write('set fmri(ncon_real) %d\n'%(len(conditions)+1+len(contrasts)))

    # loop through EVs
    convals_real=N.zeros(nevs*2)
    convals_orig=N.zeros(nevs)
    empty_evs=[]

    for ev in range(len(conditions)):
        outfile.write('\n\nset fmri(evtitle%d) "%s"\n'%(ev+1,conditions[ev]))

        if os.path.exists(cond_key_json):
            condfile='%s/onsets/%s'%(model_subdir,ev_files[ev])
            if os.path.exists(condfile+'.txt'):
                condfile+='.txt'
            elif os.path.exists(condfile+'.tsv'):
                condfile+='.tsv'
            """
            else:
                print "ERROR: EV files must be .txt or .tsv files. Files with name %s not found."%(condfile)
                sys.exit(-1)
            """
        else:
            condfile='%s/onsets/%s_task-%s_run-%s_ev-%03d.txt'%(model_subdir,subid_ses,taskname,runname,ev+1)
        if os.path.exists(condfile):
            outfile.write('set fmri(shape%d) 3\n'%(ev+1))
            outfile.write('set fmri(custom%d) "%s"\n'%(ev+1,condfile))
        else:
             outfile.write('set fmri(shape%d) 10\n'%(ev+1))
             print '%s is missing, using empty EV'%condfile
             empty_evs.append(ev+1)
             
        outfile.write('set fmri(convolve%d) 3\n'%(ev+1))
        outfile.write('set fmri(convolve_phase%d) 0\n'%(ev+1))
        outfile.write('set fmri(tempfilt_yn%d) 1\n'%(ev+1))
        outfile.write('set fmri(deriv_yn%d) 1\n'%(ev+1))

        # first write the orth flag for zero, which seems to be turned on whenever
        # anything is orthogonalized
        
        if orth.has_key(ev+1):
                outfile.write('set fmri(ortho%d.0) 1\n'%int(ev+1))
        else:
                outfile.write('set fmri(ortho%d.0) 0\n'%int(ev+1))
        
        for evn in range(1,nevs+1):
            if orth.has_key(ev+1):
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
                
    if len(empty_evs)>0:
        empty_ev_file=open('%s/onsets/%s_task-%s_run-%s_empty_evs.txt'%(model_subdir,subid_ses,taskname,runname),'w')
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
        print contrasts
        contrastctr=ev+3;
        for c in contrasts.iterkeys():
            
            outfile.write('set fmri(conpic_real.%d) 1\n'%contrastctr)
            outfile.write('set fmri(conname_real.%d) "%s"\n'%(contrastctr,c))
            outfile.write('set fmri(conname_orig.%d) "%s"\n'%(contrastctr,c))
            cveclen=len(contrasts[c])
            con_real_ctr=1
            for evt in range(nevs):
                if contrasts[c][evt]!=0:
                    outfile.write('set fmri(con_real%d.%d) %s\n'%(contrastctr,con_real_ctr,contrasts[c][evt]))
                    outfile.write('set fmri(con_real%d.%d) 0\n'%(contrastctr,con_real_ctr+1))
                    con_real_ctr+=2
                    
                else:
                    outfile.write('set fmri(con_real%d.%d) 0\n'%(contrastctr,evt+1))
                    
            for evt in range(nevs):
                if evt<cveclen:
                    outfile.write('set fmri(con_orig%d.%d) %s\n'%(contrastctr,evt+1,contrasts[c][evt]))
                else:
                    outfile.write('set fmri(con_orig%d.%d) 0\n'%(contrastctr,evt+1))

            contrastctr+=1
    # Add confound EVs text file
    #confoundfile="%s/BOLD/task%03d_run%03d/QA/confound.txt"%(fmriprep_subdir,tasknum,runname)
    #confoundfile="%s/func/QA/confound.txt"%(fmriprep_subdir)
    confoundfile='%s/onsets/%s_task-%s_run-%s_ev-confounds.tsv'%(model_subdir,subid_ses,taskname,runname)
    if os.path.exists(confoundfile) and confound:
        outfile.write('set fmri(confoundevs) 1\n')
        outfile.write('set confoundev_files(1) "%s"\n'%confoundfile)
    else:
        print "No confounds file found"
        outfile.write('set fmri(confoundevs) 0\n')
        
    outfile.close()

    if callfeat:
        featargs = ["feat",outfilename]
        print "Calling", ' '.join(featargs)
        sub.call(featargs)

    return outfilename

if __name__ == '__main__':
    main()
