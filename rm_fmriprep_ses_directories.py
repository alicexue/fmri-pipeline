import sys
import os
import subprocess as sp

"""
Takes path to fmriprep directory and removes session-level directories 
If anat and func folders exist under the session directory, they are copied to the directory above the session directory
 (the subject folder)
Files in the anat and func folders are renamed accordingly (session labels are removed)

(note: for use with Flywheel downloads that have session labels)
"""

# Created by Alice Xue, 06/2019

if len(sys.argv) < 2:
    print("usage: rm_fmriprep_ses_directories.py <fmriprep directory path>")
    sys.exit()

fmriprep_dir = sys.argv[1]

subjids = []
potential_subs = os.listdir(fmriprep_dir)
for s in potential_subs:
    if s.startswith('sub-'):
        subjids.append(s)

# look for session directories in each subject folder 
for sub in subjids:
    subdir = os.path.join(fmriprep_dir, sub)
    if os.path.isdir(subdir):
        subdir_contents = os.listdir(subdir)
        containsAnatDir = False
        if 'anat' in subdir_contents:
            containsAnatDir = True
        for d in subdir_contents:
            if d.startswith('ses-'):
                sesdir = os.path.join(fmriprep_dir, sub, d)
                sesdir_contents = os.listdir(sesdir)
                funcdir = os.path.join(sesdir, 'func')
                if os.path.exists(funcdir):  # look for func directory in sessiondir_contents
                    print("Moving %s to %s" % (funcdir, subdir))  # move func dir to sub dir
                    sp.call(['mv', funcdir, subdir])
                anatdir = os.path.join(sesdir, 'anat')
                if os.path.exists(anatdir):
                    print("Copying contents of %s to %s" % (
                        anatdir, subdir))  # copy anat dir (under session dir) contents to sub dir anat dir
                    sp.call(['cp', '-r', anatdir, subdir])
                print("Removing %s" % sesdir)
                sp.call(['rm', '-r', sesdir])

for sub in subjids:
    subdir = os.path.join(fmriprep_dir, sub)
    # rename files in the funcdir and anat dir - remove 'ses-' tag if it exists
    dirs = ['anat', 'func', 'figures']
    for d in dirs:
        newdir = os.path.join(subdir, d)
        if os.path.isdir(newdir):
            allfiles = os.listdir(newdir)
            for filename in allfiles:
                if '_ses-' in filename:
                    i1 = filename.find('_ses-')
                    i2 = filename[i1 + 1:].find('_') + 1
                    newfilename = filename[:i1] + filename[i1 + i2:]
                    newfilepath = os.path.join(newdir, newfilename)
                    print("Renaming %s to %s" % (filename, newfilename))
                    sp.call(['mv', os.path.join(newdir, filename), newfilepath])
