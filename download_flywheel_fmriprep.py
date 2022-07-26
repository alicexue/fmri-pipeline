#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Downloads each subject's fmriprep outputs (func and anat, reports, freesurfer) from flywheel
Iterates through all the sessions and analyses
Checks if the subject's fmriprep, freesurfer, and reports folder for the given session have already been downloaded
Will not overwrite existing fmriprep and reports folders (will print a skip message)
If fmriprep was run multiple times, downloads the most recent analysis
Downloads everything into a tmp folder
Each subject's fmriprep folder is moved to the fmriprep directory under the directory basedir+studyid
The html and svg outputs are moved to the reports directory (which is at the same level as the fmriprep directory)
When download is complete, the tmp folder is removed

Notes:
- Only freesurfer for 1 session is downloaded
"""

# Created by Alice Xue, 06/2018

import flywheel
import os
import re
import subprocess as sp


def unzip_dir(dir_from, dir_to):
    print('Unzipping', dir_from, 'to', dir_to)
    sp.call(['unzip', dir_from, '-d', dir_to])


def move_dir(dir_from, dir_to):
    print('Moving %s to %s' % (dir_from, dir_to))
    sp.call(['mv', dir_from, dir_to])


def rename_dir(dir_from, dir_to):
    print('Renaming %s to %s' % (dir_from, dir_to))
    sp.call(['mv', dir_from, dir_to])


def remove_dir(dir_name):
    if os.path.exists(dir_name):
        print("Removing %s" % dir_name)
        sp.call(['rm', '-rf', dir_name])


# get subjects on flywheel that have fmriprep outputs
# ses_level_fmriprep: <boolean> indicating whether the desired fmriprep outputs were run at the subject or session level
def get_flywheel_subjects(key, group_id, project_label, ses_level_fmriprep):
    # Create client
    fw = flywheel.Client(key)  # API key
    subs = []

    if ses_level_fmriprep:
        # Iterates through given project
        for project in fw.get_group_projects(group_id):
            if project.label == project_label:
                print('Project: %s: %s' % (project.id, project.label))
                # Iterates through sessions in project
                for session in fw.get_project_sessions(project.id):
                    # Finds subject id for session
                    if 'BIDS' in session.info:
                        sub = session.info['BIDS']['Subject']
                        for analysis in fw.get_session_analyses(session.id):
                            # looks for fmriprep analyses
                            if 'fmriprep' in analysis.label:
                                if analysis.files is not None:  # checks for output files - that fmriprep succeeded
                                    if sub not in subs:
                                        subs.append(sub)
    else:  # subject level
        # Iterates through given project
        for project in fw.get_group_projects(group_id):
            if project.label == project_label:
                print('Project: %s: %s' % (project.id, project.label))
                # Iterates through sessions in project
                for subject in fw.get_project_subjects(project.id):
                    # Finds subject id for session
                    sub = subject['code'].replace('_', '')  # remove underscores from the subject "code"
                    for analysis in fw.get_subject_analyses(subject.id):
                        # looks for fmriprep analyses
                        if 'fmriprep' in analysis.label:
                            if analysis.files is not None:  # checks for output files - that fmriprep succeeded
                                if sub not in subs:
                                    subs.append(sub)
    subs.sort()
    return subs


def remove_existing_sub_dirs_to_overwrite_later(studyid, basedir, subjectList, downloadReports, downloadFmriprep,
                                                downloadFreesurfer):
    studydir = os.path.join(basedir, studyid)
    fmriprepdir = os.path.join(studydir, 'fmriprep')
    freesurferdir = os.path.join(studydir, 'freesurfer')
    reportsdir = os.path.join(studydir, 'reports')
    print('Removing directories to overwrite them later on:')
    for sub in subjectList:
        if downloadReports and os.path.exists(reportsdir):
            subdir = os.path.join(reportsdir, 'sub-' + sub)
            remove_dir(subdir)
            subdir = os.path.join(reportsdir, 'sub-' + sub + '.html')
            remove_dir(subdir)
        if downloadFmriprep and os.path.exists(fmriprepdir):
            subdir = os.path.join(fmriprepdir, 'sub-' + sub)
            remove_dir(subdir)
        if downloadFreesurfer and os.path.exists(freesurferdir):
            subdir = os.path.join(freesurferdir, 'sub-' + sub)
            remove_dir(subdir)
    print('\n')


def perform_session_level_fmriprep_download(fw, group_id, project_label, downloadReports, downloadFmriprep,
                                            downloadFreesurfer, ignoreSessionLabel, subjectList,
                                            overwriteSubjectOutputs,
                                            ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir):
    print('\n## Downloading fmriprep outputs now ##\n')
    # Iterates through given project
    for project in fw.get_group_projects(group_id):
        if project.label == project_label:
            print('Project: %s: %s' % (project.id, project.label))
            for session in fw.get_project_sessions(project.id):
                if 'BIDS' not in session.info:
                    break
                sub = session.info['BIDS']['Subject']
                if sub in subjectList:
                    dates = []
                    analysis_ids = {}  # key is date, value is analysis.id
                    analysis_objs = {}  # key is analysis.id, value is analysis object
                    for analysis in fw.get_session_analyses(session.id):
                        # looks for fmriprep analyses
                        if 'fmriprep' in analysis.label:
                            print('\tAnalysis: %s: %s' % (analysis.id, analysis.label))
                            date_created = analysis.created
                            analysis_ids[date_created] = analysis.id
                            analysis_objs[analysis.id] = analysis
                            if analysis.files is not None:  # checks for output files - that fmriprep succeeded
                                dates.append(date_created)

                    if len(dates) != 0:
                        list.sort(dates)

                        most_recent_analysis_id = analysis_ids[dates[-1]]
                        # if fmriprep was run multiple times, uses most recent analysis

                        # iterate through files to get the subject id (yes, this is an inefficient solution)
                        for file in analysis_objs[most_recent_analysis_id].files:
                            name = file.name
                            # assumes subject ID is between sub- and _ or between sub- and .
                            if 'sub-' in name:
                                i1 = name.find('sub-')
                                tmpname = name[i1:]
                                i2 = tmpname.find('_') if '_' in tmpname else tmpname.find('.')
                                if i1 > -1 and i2 > -1:  # if subject ID was found
                                    sub = tmpname[:i2]  # sub is the subject ID with 'sub-' removed
                                    # print("Subject ID:", sub)

                        for file in analysis_objs[most_recent_analysis_id].files:
                            # get fmriprep reports (html and svg files)
                            if downloadReports and 'html.zip' in file.name:  # sub-<id>_<alphanumeric code>.html.zip
                                subreportsdir = os.path.join(reportsdir, sub)
                                session_label = session['label']
                                print("SESSION", session_label)
                                session_label = re.sub(r'[^a-zA-Z0-9]+', '',
                                                       session_label)  # remove non-alphanumeric characters
                                subsesreportsdir = os.path.join(reportsdir, sub, 'ses-' + session_label)
                                if not ignoreSessionLabel and os.path.exists(
                                        subsesreportsdir) and not overwriteSubjectOutputs:
                                    print(
                                        'Skipping downloading and processing of fmriprep reports for %s/ses-%s'
                                        % (sub, session_label))
                                elif ignoreSessionLabel and os.path.exists(
                                        subreportsdir) and not overwriteSubjectOutputs:
                                    print('Skipping downloading and processing of fmriprep reports for %s' % (
                                        sub))
                                else:
                                    downloadSessionOnly = not ignoreSessionLabel
                                    # download the file
                                    outfile = sub + '.html.zip'
                                    print('Downloading', sub + '/ses-' + session_label + ':', file.name)
                                    filepath = os.path.join(tmpdir, outfile)
                                    fw.download_output_from_session_analysis(session.id,
                                                                             most_recent_analysis_id, file.name,
                                                                             filepath)
                                    unzippedfilepath = filepath[:-4]
                                    # unzip the file
                                    unzip_dir(filepath, unzippedfilepath)

                                    # Move sub folder in sub-<id>.html->...->sub-<id> to the
                                    # reportsdir iterates through the flywheel folder to find sub folder buried
                                    # inside the variable i is used to avoid an infinite loop
                                    i = 10
                                    curdir = ''
                                    fullcurdir = os.path.join(unzippedfilepath)
                                    while i > 0 and curdir != sub:
                                        if sub in os.listdir(fullcurdir):
                                            desireddir = os.path.join(fullcurdir, sub)
                                            targetdir = reportsdir
                                            if downloadSessionOnly:
                                                desireddir = os.path.join(fullcurdir, sub)
                                                targetdir = os.path.join(reportsdir, sub,
                                                                         'ses-' + session_label)
                                                if not os.path.exists(os.path.join(reportsdir, sub,
                                                                                   'ses-' + session_label)):
                                                    os.makedirs(os.path.join(reportsdir, sub,
                                                                             'ses-' + session_label))
                                            if os.path.exists(desireddir):
                                                move_dir(desireddir, targetdir)
                                        if len(os.listdir(fullcurdir)) > 0:
                                            # assuming only one directory in fullcurdir
                                            for folder in os.listdir(fullcurdir):
                                                if os.path.isdir(os.path.join(fullcurdir, folder)):
                                                    curdir = folder
                                                    fullcurdir = os.path.join(fullcurdir, folder)
                                        i -= 1
                                    # moves and renames index.html to sub-<id>.html
                                    indexhtmlpath = os.path.join(unzippedfilepath, 'index.html')
                                    if os.path.exists(indexhtmlpath):
                                        subreportsdir = os.path.join(reportsdir, sub)
                                        move_dir(indexhtmlpath, subreportsdir)
                                        oldindexhtml = os.path.join(subreportsdir, 'index.html')
                                        if not os.path.exists(os.path.join(subreportsdir, 'ses-' + session_label)):
                                            os.makedirs(os.path.join(subreportsdir, 'ses-' + session_label))
                                        newindexhtml = os.path.join(subreportsdir, 'ses-' + session_label,
                                                                    '%s.html' % sub)
                                        # newindexhtml = os.path.join(reportsdir, '%s.html' % sub)
                                        move_dir(oldindexhtml, newindexhtml)
                                    # move figures directory
                                    figurespath = os.path.join(unzippedfilepath, sub, 'figures')
                                    if os.path.exists(figurespath):
                                        if not os.path.exists(os.path.join(reportsdir, sub,
                                                                           'ses-' + session_label)):
                                            os.mkdir(os.path.join(reportsdir, sub, 'ses-' + session_label))
                                        subreportsdir = os.path.join(reportsdir, sub, 'ses-' + session_label)
                                        move_dir(figurespath, subreportsdir)

                                    # remove originally downloaded files
                                    remove_dir(filepath)
                                    remove_dir(unzippedfilepath)

                            # get fmriprep outputs
                            elif (downloadFmriprep or downloadFreesurfer) and \
                                    (file.name.startswith('fmriprep_' + sub) or
                                     'bids-fmriprep' in file.name):
                                # here it is looking for the following zip files
                                # fmriprep_sub-<subid>_<alphanumericcode?>.zip (this was the name pre-2022)
                                # bids-fmriprep_<session number, i think>_<alphanumericcode>.zip (2022-?)
                                subfmriprepdir = os.path.join(fmriprepdir, sub)
                                subfreesurferdir = os.path.join(freesurferdir, sub)
                                session_label = session['label']
                                session_label = re.sub(r'[^a-zA-Z0-9]+', '',
                                                       session_label)  # remove non-alphanumeric characters
                                subsesfmriprepdir = os.path.join(fmriprepdir, sub, 'ses-' + session_label)
                                continueFmriprepDownload = downloadFmriprep
                                continueFreesurferDownload = downloadFreesurfer
                                if not ignoreSessionLabel and downloadFmriprep and os.path.exists(
                                        subsesfmriprepdir) and not overwriteSubjectOutputs:
                                    print(
                                        'Skipping downloading and processing of fmriprep outputs for %s/ses-%s'
                                        % (sub, session_label))
                                    continueFmriprepDownload = False
                                elif ignoreSessionLabel and downloadFmriprep and os.path.exists(
                                        subfmriprepdir) and not overwriteSubjectOutputs:
                                    print('Skipping downloading and processing of fmriprep outputs for %s' % (
                                        sub))
                                    continueFmriprepDownload = False
                                if not ignoreSessionLabel and downloadFreesurfer and os.path.exists(
                                        subfreesurferdir) and not overwriteSubjectOutputs:
                                    print(
                                        'Skipping downloading and processing of freesurfer outputs for %s'
                                        % sub)
                                    continueFreesurferDownload = False

                                if continueFmriprepDownload or continueFreesurferDownload:
                                    downloadSessionOnly = True if os.path.exists(subfmriprepdir) and \
                                                                  not ignoreSessionLabel else False
                                    outfile = sub + '.zip'
                                    # downloads outputs
                                    print('Downloading', sub + '/ses-' + session_label + ':', file.name)
                                    filepath = os.path.join(tmpdir, outfile)
                                    fw.download_output_from_session_analysis(session.id,
                                                                             most_recent_analysis_id, file.name,
                                                                             filepath)
                                    # download_request = fw.download_session_analysis_outputs(session.id,
                                    # most_recent_analysis_id, ticket='') fw.download_ticket(
                                    # download_request.ticket, filepath)
                                    # unzips outputs
                                    unzippedfilepath = filepath[:-4]  # removes .zip from name
                                    unzip_dir(filepath, unzippedfilepath)

                                    # Move downloaded fmriprep folder to fmriprep
                                    newsubfmriprep = os.path.join(fmriprepdir, '%s' % sub)

                                    # iterates through the unzipped sub folder to find fmriprep folder buried
                                    # inside
                                    # the variable i is used to avoid an infinite loop
                                    i = 3
                                    curdir = ''
                                    fullcurdir = unzippedfilepath
                                    moved = False
                                    while i > 0 and curdir != 'fmriprep' and curdir != 'freesurfer':
                                        if downloadFmriprep and continueFmriprepDownload and 'fmriprep' in \
                                                os.listdir(fullcurdir):
                                            desireddir = os.path.join(fullcurdir, 'fmriprep', sub)
                                            targetdir = fmriprepdir
                                            if downloadSessionOnly:
                                                desireddir = os.path.join(fullcurdir, 'fmriprep', sub,
                                                                          'ses-' + session_label)
                                                targetdir = os.path.join(fmriprepdir, sub)

                                            if os.path.exists(desireddir):
                                                move_dir(desireddir, targetdir)
                                                moved = True
                                        if downloadFreesurfer and continueFreesurferDownload and 'freesurfer' \
                                                in os.listdir(fullcurdir):
                                            tmpsubfreesurferdir = os.path.join(fullcurdir, 'freesurfer', sub)
                                            if os.path.exists(tmpsubfreesurferdir) and not os.path.exists(
                                                    os.path.join(freesurferdir, sub)):
                                                move_dir(tmpsubfreesurferdir, freesurferdir)
                                                moved = True
                                        if len(os.listdir(fullcurdir)) > 0:
                                            # assuming only one directory in fullcurdir
                                            for folder in os.listdir(fullcurdir):
                                                if os.path.isdir(os.path.join(fullcurdir, folder)):
                                                    curdir = folder
                                                    fullcurdir = os.path.join(fullcurdir, folder)
                                        i -= 1
                                    if downloadFmriprep and not moved:
                                        print("Could not find fmriprep in %s" % fullcurdir)

                                    # Remove figures directory from sub folder in fmriprep the figures
                                    # directory is a duplicate of the fmriprep reports, which are downloaded
                                    # separately into the reports directory
                                    fmriprepsubfigures = os.path.join(newsubfmriprep, 'figures')

                                    remove_dir(fmriprepsubfigures)
                                    remove_dir(filepath)
                                    remove_dir(unzippedfilepath)


def perform_subject_level_fmriprep_download(fw, group_id, project_label, downloadReports, downloadFmriprep,
                                            downloadFreesurfer, ignoreSessionLabel, subjectList,
                                            overwriteSubjectOutputs,
                                            ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir):
    print('\n## Downloading fmriprep outputs now ##\n')
    # Iterates through given project
    for project in fw.get_group_projects(group_id):
        if project.label == project_label:
            print('Project: %s: %s' % (project.id, project.label))
            for subject in fw.get_project_subjects(project.id):
                # Finds subject id for session
                sub = subject['code'].replace('_', '')  # remove underscores from the subject "code"
                if sub in subjectList:
                    dates = []
                    analysis_ids = {}  # key is date, value is analysis.id
                    analysis_objs = {}  # key is analysis.id, value is analysis object
                    for analysis in fw.get_subject_analyses(subject.id):
                        # looks for fmriprep analyses
                        if 'fmriprep' in analysis.label:
                            print('\tAnalysis: %s: %s' % (analysis.id, analysis.label))
                            date_created = analysis.created
                            analysis_ids[date_created] = analysis.id
                            analysis_objs[analysis.id] = analysis
                            if analysis.files is not None:  # checks for output files - that fmriprep succeeded
                                dates.append(date_created)

                    if len(dates) != 0:
                        list.sort(dates)

                        most_recent_analysis_id = analysis_ids[dates[-1]]
                        # if fmriprep was run multiple times, uses most recent analysis

                        # iterate through files to get the subject id (yes, this is an inefficient solution)
                        for file in analysis_objs[most_recent_analysis_id].files:
                            name = file.name
                            # assumes subject ID is between sub- and _ or between sub- and .
                            if 'sub-' in name:
                                i1 = name.find('sub-')
                                tmpname = name[i1:]
                                i2 = tmpname.find('_') if '_' in tmpname else tmpname.find('.')
                                if i1 > -1 and i2 > -1:  # if subject ID was found
                                    sub = tmpname[:i2]  # sub is the subject ID with 'sub-' removed
                                    # print("Subject ID:", sub)

                        for file in analysis_objs[most_recent_analysis_id].files:
                            # get fmriprep reports (html and svg files)
                            if downloadReports and 'html.zip' in file.name:  # sub-<id>_<alphanumeric code>.html.zip
                                subreportsdir = os.path.join(reportsdir, sub)
                                if os.path.exists(subreportsdir) and not overwriteSubjectOutputs:
                                    print('Skipping downloading and processing of fmriprep reports for %s' % (sub))
                                else:
                                    # download the file
                                    outfile = sub + '.html.zip'
                                    print('Downloading', sub + ':', file.name)
                                    filepath = os.path.join(tmpdir, outfile)
                                    fw.download_output_from_subject_analysis(subject.id,
                                                                             most_recent_analysis_id, file.name,
                                                                             filepath)
                                    unzippedfilepath = filepath[:-4]
                                    # unzip the file
                                    unzip_dir(filepath, unzippedfilepath)

                                    # Move sub folder in sub-<id>.html->...->sub-<id> to the
                                    # reportsdir iterates through the flywheel folder to find sub folder buried
                                    # inside the variable i is used to avoid an infinite loop
                                    i = 10
                                    curdir = ''
                                    fullcurdir = os.path.join(unzippedfilepath)
                                    while i > 0 and curdir != sub:
                                        if sub in os.listdir(fullcurdir):
                                            desireddir = os.path.join(fullcurdir, sub)
                                            targetdir = reportsdir
                                            if os.path.exists(desireddir):
                                                move_dir(desireddir, targetdir)
                                        if len(os.listdir(fullcurdir)) > 0:
                                            # assuming only one directory in fullcurdir
                                            for folder in os.listdir(fullcurdir):
                                                if os.path.isdir(os.path.join(fullcurdir, folder)):
                                                    curdir = folder
                                                    fullcurdir = os.path.join(fullcurdir, folder)
                                        i -= 1
                                    # moves and renames index.html to sub-<id>.html
                                    indexhtmlpath = os.path.join(unzippedfilepath, 'index.html')
                                    if os.path.exists(indexhtmlpath):
                                        subreportsdir = os.path.join(reportsdir, sub)
                                        move_dir(indexhtmlpath, subreportsdir)
                                        oldindexhtml = os.path.join(subreportsdir, 'index.html')
                                        newindexhtml = os.path.join(subreportsdir, '%s.html' % sub)
                                        move_dir(oldindexhtml, newindexhtml)
                                    # move figures directory
                                    figurespath = os.path.join(unzippedfilepath, sub, 'figures')
                                    if os.path.exists(figurespath):
                                        subreportsdir = os.path.join(reportsdir, sub)
                                        move_dir(figurespath, subreportsdir)

                                    # remove originally downloaded files
                                    remove_dir(filepath)
                                    remove_dir(unzippedfilepath)

                            # get fmriprep outputs
                            elif (downloadFmriprep or downloadFreesurfer) and \
                                    (file.name.startswith('fmriprep_' + sub) or
                                     'bids-fmriprep' in file.name):
                                # here it is looking for the following zip files
                                # fmriprep_sub-<subid>_<alphanumericcode?>.zip (this was the name pre-2022)
                                # bids-fmriprep_<session number, i think>_<alphanumericcode>.zip (2022-?)
                                subfmriprepdir = os.path.join(fmriprepdir, sub)
                                subfreesurferdir = os.path.join(freesurferdir, sub)
                                continueFmriprepDownload = downloadFmriprep
                                continueFreesurferDownload = downloadFreesurfer
                                if downloadFmriprep and os.path.exists(
                                        subfmriprepdir) and not overwriteSubjectOutputs:
                                    print('Skipping downloading and processing of fmriprep outputs for %s' % (
                                        sub))
                                    continueFmriprepDownload = False
                                if downloadFreesurfer and os.path.exists(
                                        subfreesurferdir) and not overwriteSubjectOutputs:
                                    print(
                                        'Skipping downloading and processing of freesurfer outputs for %s'
                                        % sub)
                                    continueFreesurferDownload = False

                                if continueFmriprepDownload or continueFreesurferDownload:
                                    outfile = sub + '.zip'
                                    # downloads outputs
                                    print('Downloading', sub + ':', file.name)
                                    filepath = os.path.join(tmpdir, outfile)
                                    fw.download_output_from_subject_analysis(subject.id,
                                                                             most_recent_analysis_id, file.name,
                                                                             filepath)
                                    # download_request = fw.download_session_analysis_outputs(session.id,
                                    # most_recent_analysis_id, ticket='') fw.download_ticket(
                                    # download_request.ticket, filepath)
                                    # unzips outputs
                                    unzippedfilepath = filepath[:-4]  # removes .zip from name
                                    unzip_dir(filepath, unzippedfilepath)

                                    # Move downloaded fmriprep folder to fmriprep
                                    newsubfmriprep = os.path.join(fmriprepdir, '%s' % sub)

                                    # iterates through the unzipped sub folder to find fmriprep folder buried
                                    # inside
                                    # the variable i is used to avoid an infinite loop
                                    i = 3
                                    curdir = ''
                                    fullcurdir = unzippedfilepath
                                    moved = False
                                    while i > 0 and curdir != 'fmriprep' and curdir != 'freesurfer':
                                        if downloadFmriprep and continueFmriprepDownload and 'fmriprep' in \
                                                os.listdir(fullcurdir):
                                            desireddir = os.path.join(fullcurdir, 'fmriprep', sub)
                                            targetdir = fmriprepdir
                                            if os.path.exists(desireddir):
                                                move_dir(desireddir, targetdir)
                                                moved = True
                                        if downloadFreesurfer and continueFreesurferDownload and 'freesurfer' \
                                                in os.listdir(fullcurdir):
                                            tmpsubfreesurferdir = os.path.join(fullcurdir, 'freesurfer', sub)
                                            if os.path.exists(tmpsubfreesurferdir) and not os.path.exists(
                                                    os.path.join(freesurferdir, sub)):
                                                move_dir(tmpsubfreesurferdir, freesurferdir)
                                                moved = True
                                        if len(os.listdir(fullcurdir)) > 0:
                                            # assuming only one directory in fullcurdir
                                            for folder in os.listdir(fullcurdir):
                                                if os.path.isdir(os.path.join(fullcurdir, folder)):
                                                    curdir = folder
                                                    fullcurdir = os.path.join(fullcurdir, folder)
                                        i -= 1
                                    if downloadFmriprep and not moved:
                                        print("Could not find fmriprep in %s" % fullcurdir)

                                    # Remove figures directory from sub folder in fmriprep the figures
                                    # directory is a duplicate of the fmriprep reports, which are downloaded
                                    # separately into the reports directory
                                    fmriprepsubfigures = os.path.join(newsubfmriprep, 'figures')

                                    remove_dir(fmriprepsubfigures)
                                    remove_dir(filepath)
                                    remove_dir(unzippedfilepath)


def download_flywheel_fmriprep(key, group_id, project_label, studyid, basedir, downloadReports, downloadFmriprep,
                               downloadFreesurfer, ignoreSessionLabel, subjectList, overwriteSubjectOutputs,
                               ses_level_fmriprep):
    # Creates tmp, fmriprep, and reports directories if they don't exist
    studydir = os.path.join(basedir, studyid)
    if not os.path.exists(studydir):
        os.mkdir(studydir)
    tmpdir = os.path.join(studydir, 'tmp')
    if os.path.exists(tmpdir):
        remove_dir(tmpdir)
    os.mkdir(tmpdir)

    fmriprepdir = os.path.join(studydir, 'fmriprep')
    if downloadFmriprep and not os.path.exists(fmriprepdir):
        os.mkdir(fmriprepdir)
    freesurferdir = os.path.join(studydir, 'freesurfer')
    if downloadFreesurfer and not os.path.exists(freesurferdir):
        os.mkdir(freesurferdir)
    reportsdir = os.path.join(studydir, 'reports')
    if downloadReports and not os.path.exists(reportsdir):
        os.mkdir(reportsdir)

    # Create client
    fw = flywheel.Client(key)  # API key

    if overwriteSubjectOutputs:
        remove_existing_sub_dirs_to_overwrite_later(studyid, basedir, subjectList, downloadReports, downloadFmriprep,
                                                    downloadFreesurfer)

    if ses_level_fmriprep:
        perform_session_level_fmriprep_download(fw, group_id, project_label, downloadReports, downloadFmriprep,
                                                downloadFreesurfer, ignoreSessionLabel, subjectList,
                                                overwriteSubjectOutputs,
                                                ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir)
    else:
        perform_subject_level_fmriprep_download(fw, group_id, project_label, downloadReports,
                                                downloadFmriprep,
                                                downloadFreesurfer, ignoreSessionLabel, subjectList,
                                                overwriteSubjectOutputs,
                                                ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir)
    # remove the tmp directory
    if os.path.exists(tmpdir):
        remove_dir(tmpdir)
