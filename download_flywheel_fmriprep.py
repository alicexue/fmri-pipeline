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


def move_dir(dir_from, dir_to, shell=False):
    # DK - 2025_02_20: support using shell to execute move, which allows for wildcard matching
    print('Moving %s to %s' % (dir_from, dir_to))
    if shell:
        sp.call(' '.join(['mv', dir_from, dir_to]), shell=shell)
    else:
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


def process_fmriprep_or_freesurfer_subdir(fullcurdir, most_recent_analysis_id, continueFmriprepDownload,
                                       downloadSessionOnly, fmriprepdir, sub, session_label,
                                       continueFreesurferDownload, freesurferdir):
    '''
    DK - 2025_02_20: Function to extract "fmriprep" (or fmriprep-like) or "freesurfer" subdir from `fullcurdir` and
    then recursively crawl remaining subdirs until these subdirs are found.

    Note: assumes that freesurfer dir is never within fmriprep dir, and vice versa (a reasonable assumption). This
        assumption is applied by fact that when we find freesurfer/fmriprep subdir, we move it out of the parent dir,
        and therefore the subdir's contents can never be crawled.

    :param fullcurdir:
    :param most_recent_analysis_id:
    :param continueFmriprepDownload:
    :param downloadSessionOnly:
    :param fmriprepdir:
    :param sub:
    :param session_label:
    :param continueFreesurferDownload:
    :param freesurferdir:
    :return:
        moved_fmriprep: flag whether fmriprep dir was found and moved
        moved_fs: flag whether freesurfer dir was found and moved
    '''

    # # debugging
    # print('Processing dir ', fullcurdir)

    # initialize
    moved_fmriprep = moved_fs = False

    # list of dir contents
    curdir_contents = os.listdir(fullcurdir)

    # convenience variable for testing special case of the
    # fmriprep-like dir from the new fmriprep layout
    contains_fmriprep_like = (most_recent_analysis_id in os.listdir(fullcurdir) and
                              'sourcedata' in os.listdir(os.path.join(fullcurdir, most_recent_analysis_id)))
    if (continueFmriprepDownload and
            ('fmriprep' in os.listdir(fullcurdir) or contains_fmriprep_like)):
        if downloadSessionOnly:
            targetdir = os.path.join(fmriprepdir, sub)
            if contains_fmriprep_like:
                desireddir = os.path.join(fullcurdir, most_recent_analysis_id, sub,
                                          'ses-' + session_label)
            else:
                desireddir = os.path.join(fullcurdir, 'fmriprep', sub,
                                          'ses-' + session_label)
        else:
            targetdir = fmriprepdir
            if contains_fmriprep_like:
                desireddir = os.path.join(fullcurdir, most_recent_analysis_id, sub)
            else:
                desireddir = os.path.join(fullcurdir, 'fmriprep', sub)

        if os.path.exists(desireddir):
            # # remove subdir from list of dir contents. this assumes that freesurfer dir is never within fmriprep dir,
            # # and vice versa
            # curdir_contents.pop(curdir_contents.index(desireddir))
            move_dir(desireddir, targetdir)
            moved_fmriprep = True

        # DK - 2025_02_20: copy additional dataset-level files to "fmriprep" dir.
        # (See inventory in comment above).
        # Note: these will overwrite any existing files.
        targetdir = fmriprepdir
        if contains_fmriprep_like:
            basedir = os.path.join(fullcurdir, most_recent_analysis_id)
        else:
            basedir = os.path.join(fullcurdir, "fmriprep")
        if os.path.exists(os.path.join(basedir, '.bidsignore')):
            move_dir(os.path.join(basedir, '.bidsignore'), targetdir)
        if os.path.exists(os.path.join(basedir, 'dataset_description.json')):
            move_dir(os.path.join(basedir, 'dataset_description.json'), targetdir)
        if os.path.exists(os.path.join(basedir, 'desc-aparcaseg_dseg.tsv')):
            move_dir(os.path.join(basedir, 'desc-aparcaseg_dseg.tsv'), targetdir)
        if os.path.exists(os.path.join(basedir, 'desc-aseg_dseg.tsv')):
            move_dir(os.path.join(basedir, 'desc-aseg_dseg.tsv'), targetdir)
        if os.path.exists(os.path.join(basedir, 'logs')):
            # logs is a dir, so if it exists at target already, must copy dir
            # contents using shell to expand wildcard *
            if os.path.exists(os.path.join(targetdir, 'logs')):
                move_dir(os.path.join(basedir, 'logs', '*'), os.path.join(
                    targetdir, 'logs'), shell=True)
            else:
                move_dir(os.path.join(basedir, 'logs'), targetdir)

    if continueFreesurferDownload and 'freesurfer' \
            in os.listdir(fullcurdir):
        tmpsubfreesurferdir = os.path.join(fullcurdir, 'freesurfer', sub)
        if os.path.exists(tmpsubfreesurferdir) and not os.path.exists(
                os.path.join(freesurferdir, sub)):
            # # remove subdir from list of dir contents. this assumes that freesurfer dir is never within fmriprep dir,
            # # and vice versa
            # curdir_contents.pop(curdir_contents.index(desireddir))
            move_dir(tmpsubfreesurferdir, freesurferdir)
            moved_fs = True
        # DK - 2025_02_20: newer versions of flywheel remove fsaverage from each
        # subject-level dir to conserve space, and save a copy at the level of
        # the "freesurfer" dir. Copy this once per dataset for use with the
        # entire dataset.
        if (os.path.exists(os.path.join(fullcurdir, 'freesurfer', "fsaverage"))
                and not os.path.exists(os.path.join(freesurferdir, "fsaverage"))):
            move_dir(os.path.join(fullcurdir, 'freesurfer', "fsaverage"),
                     os.path.join(freesurferdir))

    # loop through remaining dir contents and recursively call present function so as to crawl each remaining
    # subdir/folder
    for folder in curdir_contents:
        if os.path.isdir(os.path.join(fullcurdir, folder)):
            (this_moved_fmriprep, this_moved_fs) = process_fmriprep_or_freesurfer_subdir(os.path.join(fullcurdir, folder),
                most_recent_analysis_id, not moved_fmriprep, downloadSessionOnly, fmriprepdir, sub,
                session_label, not moved_fs, freesurferdir)

            # update existing flags
            moved_fmriprep = moved_fmriprep or this_moved_fmriprep
            moved_fs = moved_fs or this_moved_fs

    return (moved_fmriprep, moved_fs)

def perform_session_level_fmriprep_download(fw, group_id, project_label, downloadReports, downloadFmriprep,
                                            downloadFreesurfer, ignoreSessionLabel, subjectList,
                                            overwriteSubjectOutputs,
                                            ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir,
                                            user_selects_analysis=False):
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
                    i = 0
                    for analysis in fw.get_session_analyses(session.id):
                        # looks for fmriprep analyses
                        if 'fmriprep' in analysis.label:
                            i+=1 # only enumerate fmriprep analyses
                            print('\tAnalysis #%d: %s: %s' % (i,analysis.id, analysis.label))
                            date_created = analysis.created
                            analysis_ids[date_created] = analysis.id
                            analysis_objs[analysis.id] = analysis
                            if analysis.files is not None:  # checks for output files - that fmriprep succeeded
                                dates.append(date_created)

                    if len(dates) != 0:
                        dates_sorted = sorted(dates)

                        # if fmriprep was run multiple times, allow user to select analysis
                        if user_selects_analysis and len(dates) > 1:
                            # DK 2025_02_19
                            # Allow user to select analysis
                            analysis_num = input('Enter analysis # to download (if empty, defaults to {}): '
                                                 ''.format(dates.index(dates_sorted[-1]) + 1))
                            while len(analysis_num) > 0 and analysis_num not in map(str,range(1,len(dates)+1)):
                                print('\nInvalid analysis #. See list of analysis #''s above')
                                analysis_num = input('Enter analysis # to download (if empty, defaults to {}): '
                                                     ''.format(dates.index(dates_sorted[-1]) + 1))
                            if len(analysis_num) == 0:
                                # set to default (i.e., most recent analysis)
                                analysis_num = dates.index(dates_sorted[-1]) + 1
                            # ensure int
                            analysis_num = int(analysis_num)
                        else:
                            # set to default (i.e., most recent analysis)
                            analysis_num = dates.index(dates_sorted[-1]) + 1

                        # convert analysis number to analysis ID. Reuse `most_recent_analysis_id` for convenience and
                        # to minimize changes below, even though id is no longer necessarily the most recent.
                        most_recent_analysis_id = analysis_ids[dates[analysis_num-1]]

                        print('\nDownloading analysis #%d: %s: %s\n' % (analysis_num, most_recent_analysis_id,
                                                                      analysis_objs[most_recent_analysis_id].label))

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

                                    # DK - 2025_02_19:
                                    # newer versions of the fmriprep gear output a single directory of the form
                                    # "sub-[...].html" (note, includes ".html", unlike earlier versions) that contains
                                    # index.html and all associated figures (i.e., no "sub-[...]" subdir and
                                    # no ""sub-[...]/figures" subdir). In this case, we simply:
                                    #   1) move "sub-[...].html" to "reports" dir
                                    #   2) rename it "sub-[...]" (remove html) to mirror how this code handles
                                    #       earlier versions of the fmriprep outputs.
                                    # We test for this case by the presence of ".html" suffix and absence of a
                                    # "figures" subdir.
                                    if (sub + '.html' == os.path.basename(unzippedfilepath) and
                                        not os.path.exists(os.path.join(unzippedfilepath, sub)) and
                                        not os.path.exists(os.path.join(unzippedfilepath, sub, 'figures'))):

                                        # move "sub-[...].html" to "reports" dir
                                        move_dir(os.path.join(unzippedfilepath), reportsdir)

                                        # rename it "sub-[...]" (remove html suffix)
                                        move_dir(os.path.join(reportsdir, sub + '.html'), os.path.join(reportsdir, sub))

                                        # SKIP remaining steps and process next file
                                        continue

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
                                                # DK - 2025_02_20: Fixing bug. Zipped output may contain multiple
                                                # "sub-[...]" folders. In this case, on the first encounter,
                                                # the whole "sub..." directory should be copied to targetdir. But on
                                                # subsequent encounters, the "sub..." dir already exists in
                                                # targetdir, and so instead the *contents* of "sub..." must be moved.
                                                # (Frankly, I think the subsequently encountered directory can be
                                                # ignored. It contains subdirs "anat" and "ses-[...]/func",
                                                # which together are redundant with the figures in "figures" plus the
                                                # HTML text included in index.html.)
                                                if not os.path.exists(os.path.join(targetdir, sub)):
                                                    move_dir(desireddir, targetdir)
                                                else:
                                                    # use shell to expand wild card "*" to include all dir contents
                                                    move_dir(os.path.join(desireddir,'*'), os.path.join(targetdir, sub), shell=True)
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

                                        # DK - 2025_02_19:
                                        # Fixes bug: formerly, if `subreportsdir` did not exist, the call `move_dir(
                                        # indexhtmlpath, subreportsdir)` would move `indexhtmlpath` to `reportsdir` and
                                        # rename it `sub` (and without the '.html').
                                        # Now we create `subreportsdir` if necessary, which allows `indexhtmlpath` to be
                                        # moved into `subreportsdir` as intended.
                                        if not os.path.exists(subreportsdir):
                                            os.makedirs(subreportsdir)

                                        move_dir(indexhtmlpath, subreportsdir)
                                        oldindexhtml = os.path.join(subreportsdir, 'index.html')
                                        # DK - 2025_02_20: added logic to introduce "ses=-" info only when NOT
                                        # ignoring session info (i.e., ignoreSessionLabel = False).
                                        if downloadSessionOnly:
                                            if not os.path.exists(os.path.join(subreportsdir, 'ses-' + session_label)):
                                                os.makedirs(os.path.join(subreportsdir, 'ses-' + session_label))
                                            newindexhtml = os.path.join(subreportsdir, 'ses-' + session_label,
                                                                        '%s.html' % sub)
                                        else:
                                            newindexhtml = os.path.join(reportsdir, '%s.html' % sub)
                                        move_dir(oldindexhtml, newindexhtml)

                                    # move figures directory
                                    # (DK - 2025_02_20: figure directory should have been moved already as part of
                                    #  the subsequent (deeper) "sub-..." dir above.
                                    #  Also, the handling of "ses-" info probably needs to be updated as above)
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
                                    # TODO: probably remove the following debugging steps...
                                    # DK - 2025_02_20: for debugging purposes, will use existing downloaded file if
                                    # available. Currently this requires placing a breakpoint here, then moving the
                                    # desired file to the newly created `tmp` dir
                                    filepath = os.path.join(tmpdir, outfile)
                                    if os.path.exists(filepath):
                                        print('Using existing file at',filepath,'for', sub + '/ses-' + session_label + ':', file.name)
                                    else:
                                        # downloads outputs
                                        print('Downloading', sub + '/ses-' + session_label + ':', file.name)
                                        fw.download_output_from_session_analysis(session.id,
                                                                                 most_recent_analysis_id, file.name,
                                                                                 filepath)
                                        # download_request = fw.download_session_analysis_outputs(session.id,
                                        # most_recent_analysis_id, ticket='') fw.download_ticket(
                                        # download_request.ticket, filepath)
                                    # unzips outputs
                                    unzippedfilepath = filepath[:-4]  # removes .zip from name
                                    unzip_dir(filepath, unzippedfilepath)

                                    # DK - 2025_02_20: updated below section to handle more recent fmriprep default
                                    # layout (i.e., `--output-layout bids`), which unlike earlier versions of fmriprep
                                    # (now replicated with `--output-layout legacy`), does not include an "fmriprep"
                                    # folder. Instead, the new "bids" layout is:
                                    #   [analysis ID] -- this is effectively the former "fmriprep" dir
                                    #       sub-[...] -- this is the former "fmriprep/sub..." dir
                                    #       sourcedata
                                    #           freesurfer
                                    #               sub-[...] -- standard freesurfer output
                                    #               fsaverage -- newer versions of flywheel remove fsaverage from each
                                    #                            subject-level dir to conserve space. this single copy
                                    #                            should be extracted (at least for one subject) for use
                                    #                            with the entire dataset.
                                    #       logs -- citation stuff. extract to "fmriprep" dir at least once for
                                    #               entire dataset
                                    #       .bidsignore -- useful so that "fmriprep" dir is bids-valid (i.e.,
                                    #                      validator will ignore non-bids items). extract to
                                    #                      "fmriprep" dir at least once for entire dataset
                                    #       dataset_description.json -- extract to "fmriprep" dir at least once for
                                    #                                   entire dataset
                                    #       desc-aparcaseg_dseg.tsv -- extract to "fmriprep" dir at least once for
                                    #                                  entire dataset
                                    #       desc-aseg_dseg.tsv -- extract to "fmriprep" dir at least once for entire dataset
                                    #       sub-[...].html -- this points to sub-[...]/figures and is redundant with
                                    #                         the reports that are downloaded separately
                                    #
                                    # Move downloaded fmriprep folder to fmriprep
                                    newsubfmriprep = os.path.join(fmriprepdir, '%s' % sub)

                                    # DK - 2025_02_20: adapted to support new fmriprep output layout where the
                                    # fmriprep-like dir (see above) and "freesurfer" dir are not in the same directory.
                                    # Rather, "freesurfer" is within [fmriprep-like]/sourcedata/freesurfer. So we can't
                                    # bail the dir crawl when we find fmriprep-like dir. Have to keep looking for
                                    # "freesurfer". Moreover, we can no longer assume there is one and only one
                                    # subdir per dir, i.e., the dir tree has multiple branches. Therefore we need a
                                    # proper dir crawler with a recursive function call, which we now do with the new
                                    # function `process_fmriprep_or_freesurfer_subdir()`
                                    fullcurdir = unzippedfilepath
                                    (moved_fmriprep, moved_fs) = process_fmriprep_or_freesurfer_subdir(fullcurdir,
                                                                          most_recent_analysis_id,
                                                                          continueFmriprepDownload,
                                                                          downloadSessionOnly, fmriprepdir, sub,
                                                                          session_label,
                                                                          continueFreesurferDownload, freesurferdir)

                                    # TODO: after review, the following huge code block can probably be removed.
                                    # DK - 2025_02_20: The following huge code block has been moved and replaced by
                                    # `process_fmriprep_or_freesurfer_subdir()` (see above), which was necessary to
                                    # adapt to fmriprep's new output layout
                                    #
                                    # # iterates through the unzipped sub folder to find fmriprep folder buried
                                    # # inside
                                    # # the variable i is used to avoid an infinite loop
                                    # i = 3
                                    # curdir = ''
                                    # fullcurdir = unzippedfilepath
                                    # moved_fmriprep = moved_fs = False
                                    #
                                    # # DK - 2025_02_20:
                                    # # handles special case where `curdir` matches `most_recent_analysis_id`. confirm
                                    # # we're dealing with the new fmriprep output layout (see above) by checking # if dir
                                    # # contains subdir "sourcedata". Only proceed if `curdur` is not this special case
                                    # # AND is not "fmriprep"
                                    # #
                                    # # while (i > 0 and (curdir != 'fmriprep'
                                    # #                  and not (curdir == most_recent_analysis_id
                                    # #                          and 'sourcedata' in os.listdir(fullcurdir))
                                    # #                  )
                                    # #                 and curdir != 'freesurfer'):
                                    #
                                    #     # DK - 2025_02_20: convenience variable for testing special case of the
                                    #     # fmriprep-like dir from the new fmriprep layout
                                    #     contains_fmriprep_like = (most_recent_analysis_id in os.listdir(fullcurdir) and
                                    #         'sourcedata' in os.listdir(os.path.join(fullcurdir, most_recent_analysis_id)))
                                    #     if (downloadFmriprep and continueFmriprepDownload and
                                    #             ('fmriprep' in os.listdir(fullcurdir) or contains_fmriprep_like)):
                                    #         if downloadSessionOnly:
                                    #             targetdir = os.path.join(fmriprepdir, sub)
                                    #             if contains_fmriprep_like:
                                    #                 desireddir = os.path.join(fullcurdir, most_recent_analysis_id, sub,
                                    #                                           'ses-' + session_label)
                                    #             else:
                                    #                 desireddir = os.path.join(fullcurdir, 'fmriprep', sub,
                                    #                                           'ses-' + session_label)
                                    #         else:
                                    #             targetdir = fmriprepdir
                                    #             if contains_fmriprep_like:
                                    #                 desireddir = os.path.join(fullcurdir, most_recent_analysis_id, sub)
                                    #             else:
                                    #                 desireddir = os.path.join(fullcurdir, 'fmriprep', sub)
                                    #
                                    #         if os.path.exists(desireddir):
                                    #             move_dir(desireddir, targetdir)
                                    #             moved_fmriprep = True
                                    #
                                    #         # DK - 2025_02_20: copy additional dataset-level files to "fmriprep" dir.
                                    #         # (See inventory in comment above).
                                    #         # Note: these will overwrite any existing files.
                                    #         targetdir = fmriprepdir
                                    #         if contains_fmriprep_like:
                                    #             basedir = os.path.join(fullcurdir, most_recent_analysis_id)
                                    #         else:
                                    #             basedir = os.path.join(fullcurdir, "fmriprep")
                                    #         if os.path.exists(os.path.join(basedir, '.bidsignore')):
                                    #             move_dir(os.path.join(basedir, '.bidsignore'), targetdir)
                                    #         if os.path.exists(os.path.join(basedir, 'dataset_description.json')):
                                    #             move_dir(os.path.join(basedir, 'dataset_description.json'), targetdir)
                                    #         if os.path.exists(os.path.join(basedir, 'desc-aparcaseg_dseg.tsv')):
                                    #             move_dir(os.path.join(basedir, 'desc-aparcaseg_dseg.tsv'), targetdir)
                                    #         if os.path.exists(os.path.join(basedir, 'desc-aseg_dseg.tsv')):
                                    #             move_dir(os.path.join(basedir, 'desc-aseg_dseg.tsv'), targetdir)
                                    #         if os.path.exists(os.path.join(basedir, 'logs')):
                                    #             # logs is a dir, so if it exists at target already, must copy dir
                                    #             # contents using shell to expand wildcard *
                                    #             if os.path.exists(os.path.join(targetdir, 'logs')):
                                    #                 move_dir(os.path.join(basedir, 'logs', '*'), os.path.join(
                                    #                     targetdir,'logs'), shell=True)
                                    #             else:
                                    #                 move_dir(os.path.join(basedir, 'logs'), targetdir)
                                    #
                                    #     if downloadFreesurfer and continueFreesurferDownload and 'freesurfer' \
                                    #             in os.listdir(fullcurdir):
                                    #         tmpsubfreesurferdir = os.path.join(fullcurdir, 'freesurfer', sub)
                                    #         if os.path.exists(tmpsubfreesurferdir) and not os.path.exists(
                                    #                 os.path.join(freesurferdir, sub)):
                                    #             move_dir(tmpsubfreesurferdir, freesurferdir)
                                    #             moved_fs = True
                                    #         # DK - 2025_02_20: newer versions of flywheel remove fsaverage from each
                                    #         # subject-level dir to conserve space, and save a copy at the level of
                                    #         # the "freesurfer" dir. Copy this once per dataset for use with the
                                    #         # entire dataset.
                                    #         if (os.path.exists(os.path.join(fullcurdir, 'freesurfer', "fsaverage"))
                                    #                 and not os.path.exists(os.path.join(freesurferdir, "fsaverage"))):
                                    #             move_dir(os.path.join(fullcurdir, 'freesurfer', "fsaverage"),
                                    #                 os.path.join(freesurferdir))
                                    #
                                    #     if len(os.listdir(fullcurdir)) > 0:
                                    #         # assuming only one directory in fullcurdir
                                    #         for folder in os.listdir(fullcurdir):
                                    #             if os.path.isdir(os.path.join(fullcurdir, folder)):
                                    #                 curdir = folder
                                    #                 fullcurdir = os.path.join(fullcurdir, folder)
                                    #     i -= 1

                                    if downloadFmriprep and not moved_fmriprep:
                                        print("Could not find fmriprep in %s" % fullcurdir)
                                    if downloadFreesurfer and not moved_fs:
                                        print("Could not find freesurfer in %s" % fullcurdir)

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

                        # TODO: DK - 2025_02_19: if like changes in `perform_session_level...`, port them here, too
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

                                    # TODO: DK - 2025_02_19: if like changes in `perform_session_level...`, port them here, too

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

                                    # TODO: DK - 2025_02_19: Potential bug. If like fix in `perform_session_level...`,
                                    #  port it here, too

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

                                    # TODO: DK - 2025_02_19: Potential bug. If like fix in `perform_session_level...`,
                                    #  port it here, too
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
                               ses_level_fmriprep, user_selects_analysis=False):
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
                                                ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir,
                                                user_selects_analysis=user_selects_analysis)
    else:
        perform_subject_level_fmriprep_download(fw, group_id, project_label, downloadReports,
                                                downloadFmriprep,
                                                downloadFreesurfer, ignoreSessionLabel, subjectList,
                                                overwriteSubjectOutputs,
                                                ses_level_fmriprep, fmriprepdir, freesurferdir, reportsdir, tmpdir)
    # remove the tmp directory
    if os.path.exists(tmpdir):
        remove_dir(tmpdir)
