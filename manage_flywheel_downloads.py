#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Takes command line input and runs download_flywheel_fmriprep and export_raw_bids accordingly
"""

# Created by Alice Xue, 06/2018

import flywheel
import os
import subprocess as sp

import download_flywheel_fmriprep
import export_raw_bids

# checks if docker is installed
dockerExists = False
try:
    FNULL = open(os.devnull, 'w')
    sp.call(['docker'], stdout=FNULL, stderr=sp.STDOUT)
    dockerExists = True
except FileNotFoundError:
    dockerExists = False

fwExists = False
try:
    FNULL = open(os.devnull, 'w')
    sp.call(['fw'], stdout=FNULL, stderr=sp.STDOUT)
    fwExists = True
except FileNotFoundError:
    fwExists = False

APIKeyFile = 'flywheel_API_key.txt'
# checks for existing APIKeyFile and uses the key stored there
if os.path.exists(APIKeyFile):
    with open(APIKeyFile, 'r') as f:
        key = f.readline()
        fw = flywheel.Client(key)
else:  # asks for the key from the command line
    loggedIn = False
    while not loggedIn:
        key = input('Enter Your Flywheel API Key: ')
        try:
            fw = flywheel.Client(key)
            loggedIn = True
            print('Your API key will now be saved in %s for future use.' % APIKeyFile)
            with open(APIKeyFile, 'w') as f:
                f.write(key)
        except FileNotFoundError:
            print('Invalid API key.')

print('If you cannot log in, delete flywheel_API_key.txt and run manage_flywheel_downloads.py again.')
self = fw.get_current_user()
print('\nYou are now logged in as %s %s.' % (self.firstname, self.lastname))

# Ask for group id
print('')
groups = fw.get_all_groups()
if len(groups) > 0:
    print('Here are your groups:')
    for group in fw.get_all_groups():
        print('%s (group id): %s' % (group.id, group.label))
group_id = input('Enter the group id: ')

# Ask for project label
print('')
projects = fw.get_group_projects(group_id)
if len(projects) > 0:
    # lists projects in this group the user has access to
    print('Here are your projects:')
    project_labels = []
    for project in projects:
        project_id = project.id
        project_labels.append(project.label)
        print('Project label: %s' % project.label)
    # asks for project label
    my_project = input('Enter the project label: ')
    while my_project not in project_labels:
        print('\nInvalid project label. See list of project labels above')
        my_project = input('Enter the project label: ')
    project_label = my_project
else:  # if no projects are found, asks to enter group id again
    while len(fw.get_group_projects(group_id)) == 0:
        print('No projects found in group %s.' % group_id)
        print('Are you sure the group id is %s?' % group_id)
        group_id = input('Enter the group id: ')
    # lists projects
    print('\nHere are your projects:')
    projects = fw.get_group_projects(group_id)
    project_labels = []
    for project in projects:
        project_id = project.id
        project_labels.append(project.label)
        print('Project label: %s' % project.label)
    my_project = input('Enter the project label: ')
    while my_project not in project_labels:
        print('\nInvalid project label. See list of project labels above')
        my_project = input('Enter the project label: ')
    project_label = my_project

# Ask for study id
print('\nThe study id is the name of the directory that the fmriprep output will be downloaded to.')
studyid = input('Enter the study id: ')
studyid = studyid.strip()
# Asks for base directory
print(
    '\nThe base directory indicates where the study id directory will be created. Please include the full path, '
    'but not the study id.')
basedir = input('Enter the base directory: ')
# Checks if base directory exists and asks again if it doesn't
while not os.path.exists(basedir):
    print('Invalid path for the base directory.')
    basedir = input('Enter the base directory: ')
    basedir = basedir.strip()

studydir = os.path.join(basedir, studyid)
if not os.path.exists(studydir):
    print('\nNote: %s does not exist. It will be created.' % studydir)
else:
    print('\nNote: %s already exists.' % studydir)

print('\nWas fmriprep run on the subject level or session level on Flywheel?')
print('Enter 1 if you would like to download fmriprep outputs from the analyses run on the SUBJECT level or 2 for'
      ' the SESSION level.')
rsp = None
while rsp != '1' and rsp != '2':
    rsp = input('Enter 1 or 2: ')
ses_level_fmriprep = False if rsp == '1' else True

print('Looking for subjects with fmriprep outputs...')
subs = download_flywheel_fmriprep.get_flywheel_subjects(key, group_id, project_label, ses_level_fmriprep)
print('\nHere are your subjects with fmriprep outputs:')
print(subs)

continuePrompt = False
restrictedDownload = False
rsp = None
while rsp != 'y' and rsp != '':
    rsp = input('Do you want to specify which subjects you would like to download data for? (y/ENTER) ')
    if rsp == 'y':
        restrictedDownload = True
        continuePrompt = True
    else:
        print('Only the remaining subjects\' data will be downloaded.')

new_subs = []
if continuePrompt:
    continuePrompt = True
    rsp = None
    print(
        'You may choose to (1) remove subjects from the list printed above or (2) create a new list of subjects to '
        'download outputs for.')
    while rsp != '1' and rsp != '2':
        rsp = input('Enter 1 or 2: ')
    if rsp == '1':  # remove subjects from list
        while continuePrompt and (rsp in subs or rsp != ''):
            print('Subjects to download outputs for: ', subs)
            print('Press ENTER when you are finished')
            rsp = input('Enter subject id to remove: ')
            if rsp in subs:
                subs.remove(rsp)
            elif rsp == '':
                break
            else:
                print('ERROR: Invalid subject id.\n')
    elif rsp == '2':  # add subjects to list
        while continuePrompt and (rsp in subs or rsp != ''):
            print('Subjects to download outputs for:', new_subs)
            print('Press ENTER when you are finished')
            rsp = input('Enter subject id to add: ')
            if rsp in subs:
                new_subs.append(rsp)
            elif rsp == '':
                break
            else:
                print('ERROR: Invalid subject id\n')

if len(new_subs) > 0:
    subs = new_subs

if rsp != '1':  # user isn't removing subjects from the original list
    print('\nDownloads from Flywheel will be restricted to the following subjects:', subs)
# print('\nNote again that subjects in this list with existing folders will be skipped')

overwriteSubjectOutputs = False
rsp = None
while rsp != 'y' and rsp != '':
    rsp = input("If subject outputs exist, do you want to overwrite them? (y/ENTER) ")
    if rsp == 'y':
        overwriteSubjectOutputs = True
    else:
        print('Existing output folders will be overwritten.')

if ses_level_fmriprep:
    # Ignore session label on flywheel (website) for purposes of downloading data?
    ignoreSessionLabel = False
    rsp = None
    while rsp != 'y' and rsp != 'n':
        print('\nDo you want to ignore the session labels provided by Flywheel for the purposes of downloading data?')
        rsp = input(
            'Enter "y" if the session labels on the Flywheel website do NOT match the session labels in the data. '
            'Otherwise, enter "n": ')
        if rsp == 'y':
            ignoreSessionLabel = True
else:
    ignoreSessionLabel = True

# Ask which outputs to download
print('')
downloadReports = False
downloadFmriprep = False
downloadFreesurfer = False
rsp = None
while rsp != 'n' and rsp != '':
    rsp = input('Do you want to download fmriprep outputs? (ENTER/n) ')
    if rsp == '':
        downloadFmriprep = True
rsp = None
while rsp != 'n' and rsp != '':
    rsp = input('Do you want to download fmriprep reports? (html and svg files) (ENTER/n) ')
    if rsp == '':
        downloadReports = True
rsp = None
while rsp != 'n' and rsp != '':
    rsp = input('Do you want to download freesurfer outputs? (ENTER/n) ')
    if rsp == '':
        downloadFreesurfer = True

# Ask if user wants to export BIDS, which is only allowed if docker is installed and running
exportRawBids = False
if dockerExists:
    rsp = None
    print('')
    while rsp != '' and rsp != 'n':
        rsp = input('Do you want to download the raw BIDS data for your subjects? (ENTER/n) ')
    if rsp == '':
        exportRawBids = True
        rsp2 = None
        while rsp2 != '' and rsp2 != 'n':
            rsp2 = input('Docker is needed to export the raw BIDS data. Is docker running? (ENTER/n) ')
        if rsp2 == 'n':
            print('Since docker is not running, raw BIDS won\'t be exported.')
            exportRawBids = False
        elif rsp2 == '' and not fwExists:
            print('Flywheel CLI not installed, which is necessary for exporting raw BIDS.')
else:
    print('Note: docker is not installed. Raw BIDS cannot be exported.')

# downloads fmriprep outputs 
if downloadFmriprep or downloadFreesurfer or downloadReports:
    download_flywheel_fmriprep.download_flywheel_fmriprep(key, group_id, project_label, studyid, basedir,
                                                          downloadReports, downloadFmriprep, downloadFreesurfer,
                                                          ignoreSessionLabel, subs, overwriteSubjectOutputs,
                                                          ses_level_fmriprep)
# exports raw BIDS (export of raw BIDS should happen after downloading fmriprep output because export_raw_bids looks
# for subjects in fmriprep folder)
if exportRawBids:
    export_raw_bids.export_raw_bids(studyid, basedir, key, group_id, project_label)
