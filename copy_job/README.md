Useful flywheel tool to create python script from existing flywheel analysis.

From terminal, call `./copy_job.py [job_id]`, where `job_id` is the job_id from flywheel.

This will create a new python script (in calling directory) that can be called to run the job through the flywheel SDK. 
You can also view this script to extract certain useful hard-coded values, like `input_files` and `config`, which serve as inputs to 
`run_flywheel_gear.py`

Most recent code is found at: https://gitlab.com/flywheel-io/public/flywheel-tutorials/-/tree/master/copy-job

-Daniel Kimmel, 25 Feb 2025