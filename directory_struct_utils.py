# Retrieves fmriprep directory structure

# Created by Alice Xue, 06/2018

import os

# right now checks first subject - doesn't verify all subjects

def get_fmriprep_dir(studydir):
	fmriprep_dir=os.path.join(studydir,'fmriprep')
	if os.path.exists(fmriprep_dir):
		return fmriprep_dir
	else:
		print "fmriprep directory not found in %s"%studydir
		return ''

def get_all_subs(studydir):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=[]
	if os.path.exists(fmriprep):
		folders=os.listdir(fmriprep)
		for folder in folders:
			if os.path.isdir(os.path.join(fmriprep,folder)) and folder.startswith('sub-'):
				i=folder.find('-')
				sub=folder[i+1:]
				all_subs.append(sub)
		list.sort(all_subs)
	return all_subs

def get_runs(funcdir,task):
	runs=[]
	files=os.listdir(funcdir)
	for f in files:
		i1=f.find('_task-'+task+'_run-')+len('_task-'+task+'_run-')
		tmp=f[i1:]
		i2=tmp.find('_')
		run=tmp[:i2]
		if (i1 > -1 and i2 > 0):
			if run not in runs:
				runs.append(run)
	list.sort(runs)
	return runs

def get_task_runs(funcdir):
	task_runs={}
	if os.path.exists(funcdir):
		files=os.listdir(funcdir)
		for f in files:
			runs=[]
			# find task name
			i1=f.find('_task-')+len('_task-')
			tmp=f[i1:]
			i2=tmp.find('_run-')
			task=tmp[:i2]
			if (i1 > -1 and i2 > -1):
				if task not in task_runs.keys():
					# find runs for this task
					task_runs[task]=get_runs(funcdir,task)
	return task_runs


def get_study_info(studydir,hasSessions):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=get_all_subs(studydir)
	info={}
	for sub in all_subs:
		subdir=os.path.join(fmriprep,'sub-'+sub)
		files=os.listdir(subdir)
		info['sub-'+sub]={}
		if hasSessions:
			 # info = {'sub-01':{'ses-01':{...}}}
			for f in files: # session folders
				if os.path.isdir(os.path.join(subdir,f)) and f.startswith('ses-'):
					funcdir=os.path.join(subdir,f,'func')
					info['sub-'+sub][f]=get_task_runs(funcdir)
		else:
			 # info = {'sub-01':{'taskname':{...}}}
			funcdir=os.path.join(subdir,'func')
			info['sub-'+sub]=get_task_runs(funcdir)
	return info
