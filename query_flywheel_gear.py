'''
Script for querying the Flywheel Gear database for jobs.
Support CLI
'''

import argparse, ast, pandas as pd

from run_flywheel_gear import RunFlywheelGear

pd.set_option('display.max_rows', None)

def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='query flywheel gear database')

    parser.add_argument('-g', '--group',
                        required=False, help='Flywheel group name.')
    parser.add_argument('-p', '--project',
                        required=False, help='Flywheel project name.')
    parser.add_argument('-s', '--subjects',
                        required=False, help='Subject name(s).', nargs='+')
    parser.add_argument('-d', '--destination_type', default='session',
                        required=False, help='Type of destination container: "session" or "subject".')
    parser.add_argument('-b', '--use_bids', default=True, type=ast.literal_eval,
                        required=False, help='Provide logical ("True" or "False") on whether to match subjects on BIDS info.'
                                             'Set to False when some destinations may not have BIDS info.')
    parser.add_argument('-j', '--job_type', default='analysis', nargs='?',
                        required=False, help='Limit to specific job type. Leave empty to not filter by job type.')
    parser.add_argument('-k', '--key', default="flywheel_API_key.txt",
                        required=False, help='Flywheel API key or path to text file with key.')
    parser.add_argument('-st', '--state', nargs='?',
                        required=False, help='Limit to specific state. Leave empty to not filter by state.')
    parser.add_argument('--cancel_jobs', default=False, action='store_true',
                        required=False, help='Cancel all jobs returned by query.')

    args = parser.parse_args(argv)
    return args

def main(argv=None):
    args = parse_command_line(argv)

    # print(args)

    df, rfg = query_jobs(**args.__dict__)

    print(df)

    return df, rfg

def query_jobs(fw=None, key="flywheel_API_key.txt", group=None, project=None, subjects=None, destination_type="session",
         use_bids=True, job_type="analysis", state=None, cancel_jobs=False, prompt_before_cancel=True):
    '''
    get dataframe of all jobs associated with project, optionally filtered by subject. must specify type of
    destination containing jobs (e.g., session, subject, ...).

    :param fw:
    :param key:
    :param group:
    :param project:
    :param subjects: (optional)
    :param destination_type:
    :param use_bids:
    :param job_type: (str) limit to this type of job, as found in job.destination.type (this is different from the
        arg `destination_type`. Set to None to not filter by type
    :param state: (str) limit jobs to the provided state ("complete", "cancelled", "failed", "running", "pending").
        Leave empty to not filter by state.
    :param cancel_jobs: (bool) Cancel all jobs returned by query.
    :param prompt_before_cancel: (bool) When canceling jobs (see `cancel_jobs`), will prompt user before cancelling.
        Set to `False` to cancel without prompt (useful when calling from outside the command line).

    :return:
    df
    rfg object
    '''

    # instantiate
    rfg = RunFlywheelGear(fw=fw, key=key, group=group, project=project)

    # get destinations
    destinations = rfg.get_destinations(subjects=subjects, destination_type=destination_type, use_bids=use_bids)

    # get all job IDs associated with destinations
    # optionally filter by job type
    if job_type:
        _job_type_str = f',destination.type={job_type}'
    else:
        _job_type_str = ''
    # optionally filter by state
    if state:
        _state_str = f',state={state}'
    else:
        _state_str = ''
    rfg.job_ids = [job.id for dest in destinations for job in rfg.fw.jobs.find(
        f'parents.{destination_type}={dest.id}' + _job_type_str + _state_str)]

    # get status
    df = rfg.get_job_status()

    # cancel above jobs?
    if cancel_jobs:
        # limit to running or pending jobs
        df_running = df[df['state'].isin(['pending', 'running'])]
        no_jobs = df_running.empty
        continue_cancel = False

        if prompt_before_cancel:
            if no_jobs:
                print('\nThere were no running or pending jobs to cancel.')
            else:
                print(f'\nThe following running or pending jobs will be cancelled. To be more selective, start over and '
                      f'provide additional filters to your query.')
                print(df_running)
                rsp = '-1' # force while loop
                while rsp != 'y' and len(rsp) > 0:
                    rsp = input('Are you sure you want to cancel the above jobs? (y/[ENTER]): ').strip()
                continue_cancel = rsp == 'y'
        else:
            continue_cancel = True

        if continue_cancel and not no_jobs:
            print('\nCancelling above running or pending jobs...')
            rfg.cancel_jobs()
            # requery jobs
            df = rfg.get_job_status()
            # print('\nThe following jobs remain:')
        else:
            print('\nNo jobs cancelled.')

    # return df and object (in case one wants to manipulate those jobs)
    return df, rfg

if __name__ == '__main__':
    main()
