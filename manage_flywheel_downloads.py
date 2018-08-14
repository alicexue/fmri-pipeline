#!/usr/bin/env python
"""
Takes command line input and runs download_flywheel_fmriprep and export_raw_bids accordingly
"""

# Created by Alice Xue, 06/2018

import flywheel
import os
import subprocess as sp
import sys

import download_flywheel_fmriprep
import export_raw_bids

# checks if docker is installed
dockerExists=False
try:
	FNULL = open(os.devnull, 'w')
	sp.call(['docker'],stdout=FNULL, stderr=sp.STDOUT)
	dockerExists=True
except:
	dockerExists=False

fwExists=False	
try:	
	FNULL = open(os.devnull, 'w')	
	sp.call(['fw'],stdout=FNULL, stderr=sp.STDOUT)	
	fwExists=True	
except:	
	fwExists=False

APIKeyFile='flywheel_API_key.txt'
# checks for existing APIKeyFile and uses the key stored there
if os.path.exists(APIKeyFile):
	with open(APIKeyFile,'r') as f:
		key = f.readline()
		fw = flywheel.Flywheel(key) 
else: # asks for the key from the command line
	loggedIn=False
	while not loggedIn:
		key=raw_input('Enter Your Flywheel API Key: ')
		try:
			fw = flywheel.Flywheel(key) 
			loggedIn=True
		except:
			print 'Invalid API key.'
	print 'Your API key will now be saved in %s for future use. Don\'t put this file on GitHub!'%APIKeyFile
	with open(APIKeyFile,'w') as f:
		f.write(key)

print 'If you cannot log in, delete flywheel_API_key.txt and run manage_flywheel_downloads.py again.'
self = fw.get_current_user()
print('\nYou are now logged in as %s %s.' % (self.firstname, self.lastname))

# Ask for group id
print ''
groups=fw.get_all_groups()
if len(groups)>0:
	print 'Here are your groups:'
	for group in fw.get_all_groups():
		print('%s: %s' % (group.id, group.label))
group_id=raw_input('Enter the group id: ')

# Ask for project label
print ''
projects=fw.get_group_projects(group_id)
if len(projects)>0:
	# lists projects in this group the user has access to
	print 'Here are your projects:'
	project_labels=[]
	for project in projects:
		project_id=project.id
		project_labels.append(project.label)
		print('Project label: %s' % (project.label))
	# asks for project label
	my_project=''
	my_project=raw_input('Enter the project label: ')
	while my_project not in project_labels:
		print '\nInvalid project label. See list of project labels above'
		my_project=raw_input('Enter the project label: ')
	project_label=my_project
else: # if no projects are found, asks to enter group id again
	while len(fw.get_group_projects(group_id))==0:
		print 'No projects found in group %s.'%(group_id)
		print 'Are you sure the group id is %s?'%(group_id)
		group_id=raw_input('Enter the group id: ')
	# lists projects
	print '\nHere are your projects:'
	projects=fw.get_group_projects(group_id)
	project_labels=[]
	for project in projects:
		project_id=project.id
		project_labels.append(project.label)
		print('Project label: %s' % (project.label))
	my_project=''
	my_project=raw_input('Enter the project label: ')
	while my_project not in project_labels:
		print '\nInvalid project label. See list of project labels above'
		my_project=raw_input('Enter the project label: ')
	project_label=my_project
	
# Ask for study id
print '\nThe study id is the name of the directory that the fmriprep output will be downloaded to.'
studyid=raw_input('Enter the study id: ')
studyid=studyid.strip()
# Asks for base directory
print '\nThe base directory is the full path of where the study id directory will be created. (Don\'t include study id here.)'
basedir=raw_input('Enter the base directory: ')
# Checks if base directory exists and asks again if it doesn't
while not os.path.exists(basedir):
	print 'Invalid base directory.'
	basedir=raw_input('Enter the base directory: ')
	basedir=basedir.strip()

studydir=os.path.join(basedir,studyid)
if not os.path.exists(studydir):
	print '\nNote: %s does not exist. It will be created.'%studydir
else:
	print '\nNote: %s already exists. Only the remaining subjects\' data will be downloaded.'%studydir

# Ask which outputs to download
downloadReports=False
downloadFmriprep=False
downloadFreesurfer=False
rsp=None
while rsp!='n' and rsp!='':
	rsp=raw_input('Do you want to download fmriprep outputs? (ENTER/n) ')
	if rsp=='':
		downloadFmriprep=True
rsp=None
while rsp!='n' and rsp!='':
	rsp=raw_input('Do you want to download fmriprep reports? (html and svg files) (ENTER/n) ')
	if rsp=='':
		downloadReports=True
rsp=None
while rsp!='n' and rsp!='':
	rsp=raw_input('Do you want to download the freesurfer outputs? (ENTER/n) ')
	if rsp=='':
		downloadFreesurfer=True

# Ask if user wants to export BIDS, which is only allowed if docker is installed and running
exportRawBids=False
if dockerExists:
	rsp=''
	print ''
	while rsp!='' and rsp!='n':
		rsp=raw_input('Do you want to download the raw BIDS data for your subjects? (ENTER/n) ')
		if rsp=='y':
			exportRawBids=True
			rsp2=''
			while rsp2!='' and rsp2!='n':
				rsp2=raw_input('Docker is needed to export the raw BIDS data. Is docker running? (ENTER/n) ')
			if rsp2=='n':
				print 'Since docker is not running, raw BIDS won\'t be exported.'
				exportRawBids=False
			elif rsp2=='' and not fwExists: 
				print 'Flywheel CLI not installed, which is necessary for exporting raw BIDS.'
else:
	print 'Note: docker is not installed. Raw BIDS cannot be exported.'

# downloads fmriprep outputs 
download_flywheel_fmriprep.download_flywheel_fmriprep(key,group_id,project_label,studyid,basedir,downloadReports,downloadFmriprep,downloadFreesurfer)
# exports raw BIDS (export of raw BIDS should happen after downloading fmriprep output because export_raw_bids looks for subjects in fmriprep folder)
if exportRawBids:
	export_raw_bids.export_raw_bids(studyid,basedir,key,group_id,project_label)
