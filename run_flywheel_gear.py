#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Run flywheel gear programmatically, allowing for multiple gear instances to run simultaneously for multiple
sessions/subjects by calling each independently using flywheel SDK.

NB: May be very helpful to separately use flywheel's `copy_job.py` script (see copy_job/copy_job.py) to translate gear
contents to python script that provides many of the required inputs.
Also see: https://gitlab.com/flywheel-io/public/flywheel-tutorials/-/tree/master/copy-job

Daniel Kimmel, 2025 Feb 24
'''
import os
from datetime import datetime

import pandas as pd, json, regex as re

import flywheel

def convert_string_to_list(s):
    if not isinstance(s, (list, tuple)):
        if isinstance(s, str):
            s = [s]
        else:
            raise TypeError("input must be a string or list or a tuple")
    return s


class RunFlywheelGear:
    '''
    Class for creating and running flywheel gear instances (jobs) programmatically.
    '''

    def __init__(self, fw=None, key="flywheel_API_key.txt", group=None, project=None):
        '''

        :param fw: Flywheel client instance. If not provided, will create generic instance:
            `fw = flywheel.Client(key)`
        :param key: (str) Flywheel API key or path to txt file with key as first line. Only used if `fw` is not
            provided. If `key` not provided, will attempt to create instance, which assumes that user is logged in to
            flywheel by calling `fw login <key>` from terminal outside of python session (depends on flywheel CLI).
        '''

        # initialize flywheel instance if not provided
        if fw is None:
            # load key from file if necessary
            if key:
                if os.path.exists(key):
                    print(f'Using flywheel API key found at {key}')
                    with open(key, 'r') as f:
                        key = f.readline()
                else:
                    print(f'No flywheel API key not found at {key}. Will attempt to initialize flywheel client without '
                          f'key using open CLI session from outside of python session (if any).')
                    key = ""
            else:
                print(f'No flywheel API key provided. Will attempt to initialize flywheel client without key using '
                      f'open CLI session from outside of python session (if any).')
            fw = flywheel.Client(key)
        self.fw = fw

        # resolve group and project
        self.group, self.project_obj = self.get_project_and_group(group=group, project=project)


    def input_files_to_objects(self, input_files):
        '''
        Helper function. Takes dict of input files and returns dict of input flywheel objects

        :param input_files: (dict) Input files for gear. Keys are input names. Values are dict with keys "container_path"
            (flywheel path to file) and "location_name" (flywheel filename). Example:
                input_files = {
                    "bidsignore": {
                        "container_path": "shohamy/Daniel_Test",
                        "location_name": "bidsignore-project-level-json-files.txt",
                    },
                    "freesurfer_license_file": {
                        "container_path": "shohamy/Daniel_Test",
                        "location_name": "license.txt",
                    },
                    }
            NB: See copy_job/copy_job.py for more details.

        :return:
            inputs: (dict) Input files for gear. Keys are input names. But values are flywheel object. Entire `inputs`
            dict can be passed to gear as "inputs".
        '''

        inputs = dict()
        for key, val in input_files.items():
            if val["container_path"][:8] == "analysis":
                path = val["container_path"][9:]
                parent_of_analysis = self.fw.lookup(path)
                # find analysis that has the right file
                analyses = parent_of_analysis.reload().analyses
                for analysis in analyses:
                    for file in analysis.files:
                        if file.name == val["location_name"]:
                            container = analysis
            else:
                container = self.fw.lookup(val["container_path"])
            inputs[key] = container.get_file(val["location_name"])
        return inputs


    def get_project_and_group(self, group=None, project=None):
            '''
            Returns flywheel `group_obj` and `project_obj` objects given `group` and `project` names.
            '''

            ### Process inputs
            # # get from object if available
            # if hasattr(self, "group") and self.group and hasattr(self, "project_obj") and self.project_obj:
            #     group = self.group
            #     project_obj = self.project_obj
            #
            #     return group, project_obj

            # assert types
            assert isinstance(group, (str, type(None)))
            assert isinstance(project, str)

            # resolve group and project
            # get project obj
            project_obj = self.fw.projects.find(f'label={project}')
            if len(project_obj) == 0:
                raise RuntimeError(f"Project {project} not found")
            # get or confirm group
            if not group:
                # infer group from project
                if len(project_obj) > 1:
                    raise RuntimeError(
                        f"'{project}' matched multiple projects. Must be more specific or provide group to "
                        f"differentiate")
                else:
                    project_obj = project_obj[0]
                group = project_obj.parents['group']
            else:
                # confirm group and/or limit to project matching provided group
                project_obj = [po for po in project_obj if po.parents['group'] == group]
                if len(project_obj) == 0:
                    raise RuntimeError(f"'{project}' was not found in group '{group}'")
                elif len(project_obj) > 1:
                    raise RuntimeError(
                        f"'{project}' matched multiple projects, even after attempting to select by group '{group}'. "
                        f"Must be more specific.")
                else:
                    project_obj = project_obj[0]

            # # store in object for future reference
            # self.group = group
            # self.project_obj = project_obj

            return group, project_obj

    def get_destinations(self, subjects=None, destination_type="session", use_bids=True):
        '''
        Returns `destinations`, a list of flywheel "destination" objects, which can be sessions, subjects,
        and possibly others types, that match the input criteria.

        :param subjects: (str or list) List of subject labels use to match destinations. Will ignore "sub-" prefix,
            if any, both in input arg and in destination labels. If no subjects provided, will include all subjects.
        :param destination_type: (str) Type of destination object to return. Currently includes "session" or "subject".
        :param use_bids: (bool) Whether to match subject label on the BIDS subject name (in info['BIDS']['Subject'])
            if available in destination's metadata. If not available, will not match the destination. When `use_bids` is
            False, will attempt to match on flywheel's subject label in metadata. Generally recommend to match on
            BIDS, since this should be more accurate, assuming project has undergone BIDS curation.
        '''

        # if subjects is not None, make sure it's are list-like
        if subjects is not None:
            subjects = convert_string_to_list(subjects)
            # if empty list, set to None
            if len(subjects) == 0:
                subjects = None

        # pointer to destination class depending on type
        if destination_type.lower() == "session":
            destinations_all = self.project_obj.sessions()
        elif destination_type.lower() == "subject":
            destinations_all = self.project_obj.subjects()
        else:
            raise RuntimeError(f"Destination type '{destination_type}' not supported.")

        # if subjects provided, limit to those provided, else use all
        if subjects is not None:
            # strip "sub-" prefix to handle variations
            subjects = [s.lstrip('sub-') for s in subjects]

            # loop through destinations and keep only those matching criteria
            destinations = []
            for d in destinations_all:
                if use_bids:
                    if 'BIDS' in d.info and 'Subject' in d.info['BIDS']:
                        if d.info['BIDS']['Subject'] in subjects:
                            destinations.append(d)
                    else:
                        print(f'Session "{d.label}", Subject "{d.subject.label}" did not have '
                              f'`<destination>.info["BIDS"]["Subject"]` and was not included.')
                else:
                    if destination_type.lower() == "session":
                        if d.subject.label.lstrip('sub-') in subjects:
                            destinations.append(d)
                    elif destination_type.lower() == "subject":
                        if d.label.lstrip('sub-') in subjects:
                            destinations.append(d)
        else:
            destinations = destinations_all

        # return
        return destinations

    def make_gear(self, gear=None, gear_version=None):
        '''

        :param gear: (str) Name of flywheel gear to use.
        :param gear_version: (str) Version of flywheel gear to use. When not provided, will use most recent version
        :return:
            gear: flywheel gear object.
        '''

        # instantiate gear
        if isinstance(gear, str):
            # prefix with "gear/"
            gear = "gears/" + gear
            # add version if available. otherwise take most recent
            if gear_version:
                gear += "/{}".format(gear_version)
            # get gear object
            gear = self.fw.lookup(gear)

        return gear


    def make_jobs(self, gear=None, gear_version=None, subjects=None, use_bids=True,
                  destination_type="session", input_files=None, config=None, config_filepath=None, analysis_label=None,
                  analysis_label_suffix=None, tags=None):
        '''
        Makes gear object and list of arguments for running flywheel gear jobs.

        :param gear: (str) Name of flywheel gear to use.
        :param gear_version: (str) Version of flywheel gear to use. When not provided, will use most recent version.
        :param subjects: (str or list) List of subject labels use to match destinations. Will ignore "sub-" prefix,
            if any, both in input arg and in destination labels. If no subjects provided, will include all subjects.
        :param use_bids: (bool) Whether to match subject label on the BIDS subject name (in info['BIDS']['Subject'])
            if available in destination's metadata. If not available, will not match the destination. When `use_bids` is
            False, will attempt to match on flywheel's subject label in metadata. Generally recommend to match on
            BIDS, since this should be more accurate, assuming project has undergone BIDS curation.
        :param destination_type: (str) Type of destination object to return. Currently includes "session" or "subject".
        :param input_files: (see input_files_to_objects())
        :param config: (dict) Dictionary of flywheel gear configuration, of the form:
              {
              "<flywheel input arg 1>": <value>,
              ...
              "<flywheel input arg N>": <value>,
              }
            NB: See copy_job/copy_job.py for more details.
        :param config_filepath: (str) Path to JSON config file that contains "input_files" and "config" as keys. Will be
            used unless specific args (e.g., `input_files` or `config`) are provided (i.e., specific args take
            precedence). See `config-bids-fmriprep.json` for example.
        :param analysis_label: (str) Custom label for analysis/job. If not provided, will use gear name plus datetime string.
        :param analysis_label_suffix: (str) Custom suffix to append to end of analysis label. (optional)
        :param tags: (str or list) Custom tag(s) to add to analysis/job.
        :return:
            Nothing is returned.
            Adds the following properties to self:
                .jobs: (as above)
                .gear: instance of flywheel gear (as returned by make_gear())
        '''

        # assert types
        assert subjects is not None
        assert isinstance(destination_type, str)
        assert isinstance(input_files, (dict, type(None)))
        assert isinstance(config, (dict, type(None)))
        assert isinstance(analysis_label, (str, type(None)))
        assert isinstance(analysis_label_suffix, (str, type(None)))
        # make sure certain inputs are list-like
        if tags is not None:
            tags = convert_string_to_list(tags)

        # instantiate gear. Though not strictly necessary at this time, it seems that it may be important in the
        # future to have gear info at the time of setting up the config and inputs.
        # store in object for future use
        self.gear = self.make_gear(gear=gear, gear_version=gear_version)

        # construct analysis label
        if not analysis_label:
            now = datetime.now()
            analysis_label = (
                f'{self.gear.gear.name} {now.strftime("%m-%d-%Y %H:%M:%S")}'
            )
        if analysis_label_suffix:
            analysis_label += analysis_label_suffix

        # if input_files or config not provided, attempt to load from file
        if not input_files or not config:
            if config_filepath is None:
                raise RuntimeError('If `input_files` and/or `config` is not provided, `config_filepath` must be '
                                   'provided.')
            with open(config_filepath, 'r') as file:
                config_data = json.load(file)

            if not input_files:
                if 'input_files' not in config_data:
                    raise RuntimeError('If `input_files` is not provided directly, it must be defined in '
                                       'JSON at `config_filepath`.')
                input_files = config_data['input_files']
            if not config:
                if 'config' not in config_data:
                    raise RuntimeError('If `config` is not provided directly, it must be defined in '
                                       'JSON at `config_filepath`.')
                config = config_data['config']

        # convert input files to dict of flywheel objects
        inputs = self.input_files_to_objects(input_files)

        # get destinations
        destinations = self.get_destinations(subjects=subjects, destination_type=destination_type, use_bids=use_bids)

        # loop through destinations, specifying job for each. Store in object for future reference
        self.jobs = []
        for d in destinations:
            self.jobs.append(dict(
                analysis_label=analysis_label,
                config=config,
                inputs=inputs,
                destination=d,
            ))

    def run_jobs(self):
        '''
        Runs all jobs stored in `self.jobs`.
        Assumes self has been updated with self.gear and self.jobs by `make_jobs`.
        :return:
            Nothing is returned. Adds the following properties to self:
                .job_ids: list of job_ids returned by remote flywheel instance referencing each job.
                .fails: list of "destination" objects (e.g., "session" or "subject" type) for which job was not successfully
                    started. NB: this does not include jobs that started but failed after execution.
        '''

        job_ids = []
        fails = []

        for job in self.jobs:
            print(f'Running gear "{self.gear.gear.name}", job "{job["analysis_label"]}" on "{job["destination"].label}"')
            try:
                _id = self.gear.run(**job)
                job_ids.append(_id)
            except Exception as e:
                print(e)
                fails.append(job['destination'])

        # store in object and return
        self.job_ids = job_ids
        self.fails = fails

        # return job_ids, fails

    def get_job_status(self):
        '''
        Returns pandas DataFrame with status of all jobs associated with `self` (as referenced in `self.job_ids`).
        '''

        if not hasattr(self, 'job_ids'):
            print('No jobs started')
            return None

        #  iteratively calling `get_job()` requires a separate http trip for each job id and therefore takes
        #  a LONG time. Instead, we get all jobs in a batch, which wasn't easy. In theory,
        #  `fw.jobs.find(id=[...])` should do this, but doesn't work for field "id". Found a hack where it works
        #  for "_id=[...]". However, this matches only one job. In theory, we could use regex and list multiple
        #  IDs (e.g., "_id=~([...]|[...])"), but the regex indicator "~" doesn't appear to be working!
        #  Flywheel suggested using the in operator `"|"`, which does work!
        jobs = self.fw.jobs.find(f'_id=|[{','.join(self.job_ids)}]')
        job_status = []
        for job in jobs:
        # for jid in self.job_ids: # old method with separate HTTP trip for each job
            # job = self.fw.get_job(jid) # old method with separate HTTP trip for each job
            # get label for some types of jobs
            if job.destination.type == 'analysis':
                try:
                    # this doesn't always work, esp for older flywheel jobs
                    label = self.fw.get_analysis(job.destination.id).label
                except:
                    label = ""
            else:
                label = ""
            # get parent subject if available
            if 'subject' in job.parents:
                subject = self.fw.get(job.parents['subject']).label
            else:
                subject = ""
            # get parent session if available
            if 'session' in job.parents:
                session = self.fw.get(job.parents['session']).label
            else:
                session = ""

            job_status.append([job.id, job.state.value, label, subject, session])

        job_df = pd.DataFrame(job_status, columns=['job_id', 'state', 'label', 'subject', 'session'])
        job_df.set_index('job_id', inplace=True)

        return job_df

    def cancel_jobs(self, filter_dict=None):
        '''
        Cancels jobs associated with `self` (as referenced in `self.job_ids`).

        :param filter_dict: (dict) Will limit cancellation to only those jobs matching the provided filters, where dict
            keys refer to the column names in `job_df` (see self.get_job_status()) and dict values refer to one or more
            values (can provide scalar or list). For example, the following `filter_dict` filters for subjects
            "sub-18042401" and "sub-18042601" and for state "pending":
                filter_dict = dict(state="pending", subject=["sub-18042401", "sub-18042601"])
        :return:
        '''

        # get job status, which includes convenient info
        df = self.get_job_status()

        # always exclude from cancellation jobs that are not "running" or "pending", since trying to cancel other jobs
        # will raise an error
        df = df[df['state'].isin(['pending','running'])]

        # if filtering
        if filter_dict is not None:
            for k, v in filter_dict.items():
                if isinstance(v, (list,tuple)):
                    df = df[df[k].isin(v)]
                else:
                    df = df[df[k] == v]

        # loop through df rows
        for row in df.itertuples():
            job = self.fw.get_job(row.Index)
            print(f'Canceling job {row.Index}: {row.label}, subject {row.subject}, session {row.session}')
            job.change_state('cancelled')


def main(fw=None, key="flywheel_API_key.txt", group=None, project=None, subjects=None, destination_type="session",
         use_bids=True, gear=None, gear_version=None, input_files=None, config=None, config_filepath=None,
         analysis_label=None, analysis_label_suffix=None, tags=None):
    '''
    Master method for running jobs with single call. Calls methods:
        __init__(): instantiates `RunFlywheelGear` object
        make_jobs(): create list of jobs (each element is a dict of arguments for single job)
        run_jobs(): runs all jobs
    For input args, see docstring for each method.

    NB: We deliberately separate the steps of making and running jobs. The reason is that one may want to customize
    the jobs further in a way not supported by the current class. By separating these steps, this allows the user to
    modify the jobs (as specified in `object.jobs`) before running them.

    :return:
        RunFlywheelGear object

    :param fw:
    :param key:
    :param group:
    :param project:
    :param subjects:
    :param destination_type:
    :param use_bids:
    :param gear:
    :param gear_version:
    :param input_files:
    :param config:
    :param config_filepath:
    :param analysis_label:
    :param analysis_label_suffix:
    :param tags:
    :return:
    '''

    # instantiate
    rfg = RunFlywheelGear(fw=fw, key=key, group=group, project=project)

    # make jobs
    rfg.make_jobs(gear=gear, gear_version=gear_version, subjects=subjects, use_bids=use_bids,
                  destination_type=destination_type, input_files=input_files, config=config,
                  config_filepath=config_filepath, analysis_label=analysis_label,
                  analysis_label_suffix=analysis_label_suffix, tags=tags)

    # NB: Deliberately separate make_jobs and run_jobs so that one could intervene at this stage and modfied jobs in
    # some custom way before running them.

    # run job
    rfg.run_jobs()

    return rfg

def cli_user_input(fw=None, key="flywheel_API_key.txt"):
    '''
    Intended to be called from command line. Interviews user to gather necessary data to run flywheel gear.

    :param fw: Flywheel client instance. If not provided, will create generic instance:
        `fw = flywheel.Client(key)`
    :param key: (str) Flywheel API key or path to txt file with key as first line. Only used if `fw` is not
        provided. If `key` not provided, will attempt to create instance, which assumes that user is logged in to
        flywheel by calling `fw login <key>` from terminal outside of python session (depends on flywheel CLI).

    Daniel Kimmel, 26 Feb 2025
    (heavily borrows initial parts from Alice Xue's manage_flywheel_downloads.py)
    '''

    # hard coded
    key_save_path = "flywheel_API_key.txt"

    # initialize flywheel instance if not provided
    if fw is None:
        try:
            # load key from file if necessary
            if key:
                if os.path.exists(key):
                    with open(key, 'r') as f:
                        key = f.readline()
            fw = flywheel.Client(key)
        except Exception as e:
            # asks for the key from the command line
            logged_in = False
            while not logged_in:
                key = input('Enter Your Flywheel API Key: ')
                try:
                    fw = flywheel.Client(key)
                    logged_in = True
                    print('Your API key will now be saved in %s for future use.' % key_save_path)
                    with open(key_save_path, 'w') as f:
                        f.write(key)
                except FileNotFoundError:
                    print('Invalid API key.')

    self = fw.get_current_user()
    print('\nYou are now logged in as %s %s.' % (self.firstname, self.lastname))

    # Ask for group id
    print('')
    groups = fw.get_all_groups()
    if len(groups) > 0:
        print('Here are your groups:')
        for group in fw.get_all_groups():
            print('%s (group id): %s (group description)' % (group.id, group.label))
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

    print('\nSet whether to run gear on the subject level or session (default) level on Flywheel?')
    print('Enter 1 if you would like to download fmriprep outputs from the analyses run on the SUBJECT level '
          '\nor 2 (or empty) for the SESSION level.')
    rsp = '3' # trigger while loop
    while len(rsp) > 0 and rsp != '1' and rsp != '2':
        rsp = input('Enter 1 or (2 or empty): ')
    if len(rsp) == 0 or rsp == '2':
        destination_type = "session"
    else:
        destination_type = "subject"

    ### MAKE OBJECT
    # Now we have enough info to instantiate a run_flywheel_gear object
    rfg = rfg = RunFlywheelGear(fw=fw, key=key, group=group_id, project=my_project)

    # download all destinations
    destinations = rfg.get_destinations(destination_type=destination_type)
    # get set of unique subjects from those destinations
    subs = {dest.subject.label for dest in destinations}
    # convert to list and sort
    subs = sorted(list(subs))

    print('\nHere are your subjects:')
    print(subs)

    continuePrompt = False
    restricted_subjects = False
    rsp = None
    while rsp != 'y' and rsp != '':
        rsp = input('Do you want to specify which subjects you would like to download data for? (y/ENTER) ').strip()
        if rsp == 'y':
            restricted_subjects = True
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
            rsp = input('Enter 1 or 2: ').strip()
        if rsp == '1':  # remove subjects from list
            while continuePrompt and (rsp in subs or rsp != ''):
                # print('Subjects to download outputs for: ', subs)
                print('Press ENTER when you are finished')
                rsp = input('Enter subject id to remove: ').strip()
                if rsp in subs:
                    subs.remove(rsp)
                elif rsp == '':
                    break
                else:
                    print('ERROR: Invalid subject id.\n')
        elif rsp == '2':  # add subjects to list
            while continuePrompt and (rsp in subs or rsp != ''):
                # print('Subjects to download outputs for:', new_subs)
                print('Press ENTER when you are finished')
                rsp = input('Enter subject id to add: ').strip()
                if rsp in subs:
                    new_subs.append(rsp)
                elif rsp == '':
                    break
                else:
                    print('ERROR: Invalid subject id\n')

    if len(new_subs) > 0:
        subs = new_subs
    del new_subs

    if restricted_subjects:
        print('\nGear will be limited to the following subjects:', subs)

    ### DETERMINE GEAR
    gear = ''
    gear_options = ['bids-fmriprep','curate-bids']
    print('\nSelect the pre-configured gear below that you would like to use.')
    for i,g in enumerate(gear_options):
        print(f'\t#{i}: {g}')
    gear_num = '-1' # to force while loop
    while len(gear_num) > 0 and gear_num not in list(map(str,range(len(gear_options)))):
        gear_num = input('Enter the number of the gear (leave empty to enter custom gear name later): ').strip()
    if gear_num:
        gear = gear_options[int(gear_num)]
    else:
        # user will provide special gear name
        gear = ''
        while len(gear) == 0:
            gear = input('\nEnter the gear name you wish to use: ').strip()

    # ask gear version
    gear_version = input('\nEnter gear version number, or leave empty to use most recent version: ').strip()

    ### Get config file
    print('Now select the config file. If building from scratch, see `copy_job` to generate file. If using from '
          'another project, note that input file paths may require updating, e.g., '
          '\n\t"container_path": "<group>/<project_name>"')
    # default config file pattern
    config_filepath_ptrn = f'^config-{gear}[\\w-]*.json$'
    # look for matching paths in current directory
    config_filepath = [p for p in os.listdir() if re.match(config_filepath_ptrn, p) is not None]
    if len(config_filepath) == 1:
        config_filepath = config_filepath[0]
        print(f'\nThe following default config file was found: {config_filepath}')
        rsp = None
        while rsp != 'n' and rsp != '':
            rsp = input('Do you want to use it? (ENTER/n) ').strip()
        if rsp == 'n':
            config_filepath = ''
    elif len(config_filepath) > 0:
        # list options and have user choose
        print('\nMultiple matching config files found:')
        for i,p in enumerate(config_filepath):
            print(f'\t#{i}: {p}')
        fnum = '-1'  # to force while loop
        while len(fnum) > 0 and fnum not in list(map(str, range(len(config_filepath)))):
            fnum = input('Enter the number of the config file (leave empty to enter custom filepath later): ').strip()
        if fnum:
            config_filepath = config_filepath[int(fnum)]
        else:
            # user will provide config file below
            config_filepath = ''

    # use custom config file
    if not os.path.exists(config_filepath):
        # raise RuntimeError(f'No config file of the form "{config_filepath_ptrn}" was found in the current directory ('
        #                    f'{os.getcwd()}).')
        print('\nConfig file is required. See "./config-bids-fmriprep.json" for example and "./copy_job/README.md" '
              'for more information.')
        config_filepath = input('Enter path to config file: ').strip()
        while not os.path.exists(config_filepath):
            print('Invalid filepath or file not found.')
            config_filepath = input('Enter path to config file: ').strip()

    # analysis label
    analysis_label_suffix = input('Enter a suffix to label the analysis (leave empty to omit): ').rstrip()

    ### MAKE AND RUN JOBS
    rfg.make_jobs(gear=gear, gear_version=gear_version, config_filepath=config_filepath,
                  subjects=subs, use_bids=True, destination_type=destination_type, analysis_label_suffix=analysis_label_suffix,
                  tags=None)

    rsp = None
    while rsp != 'n' and rsp != '':
        rsp = input(f'Do you want to run the {len(rfg.jobs)} jobs? (ENTER/n) ').strip()
        if rsp == 'n':
            print('Quitting...')
            return None

    rfg.run_jobs()

    # job status
    df_status = rfg.get_job_status()

    print(f'The following {len(rfg.job_ids)} jobs were started:')
    print(df_status)

    # usually unnecessary when called from command line, but in case called from python, return new rfg object
    return rfg

if __name__ == '__main__':
    cli_user_input()