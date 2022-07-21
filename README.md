# fmri-pipeline

## Overview
- Neuroimaging data stored on [Flywheel](https://flywheel.io/) - including raw BIDS, fmriprep outputs, freesurfer outputs, and html/svg reports - can be downloaded using manage_flywheel_downloads.py. Fmriprep outputs are saved in [BIDS](https://bids.neuroimaging.io/) format.  
- Creates *.fsf files (see [FSL FEAT](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FEAT)) for level 1 (individual runs), level 2 (subject), and level 3 (group) analysis of fMRI data. This pipeline assumes that the user is familiar with FSL.
- Runs FSL's feat on the generated *.fsf files on high performance computing clusters in parallel using [slurm](https://hpc-wiki.info/hpc/SLURM) job arrays. If a cluster is not being used (the pipeline will detect if the sbatch command is unavailable), feat can be run on each .fsf file serially or in parallel using [joblib](https://joblib.readthedocs.io/en/latest/).

## Requirements

- Install the packages in requirements.txt. To do this in one fell swoop, use `pip install -r requirements.txt`. Note that on a cluster, you may want to install these packages in a virtual environment.
- [Install FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation). Note that you may need to modify your .bash_profile (some guidance [here](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation/ShellSetup)).

#### For downloading data from Flywheel:
- Have your Flywheel API key handy (see your user profile). 
- To export raw BIDS, you must have [Docker](https://docs.docker.com/get-docker/) installed and running, and the [Flywheel CLI](https://docs.flywheel.io/hc/en-us/articles/360008162214-Installing-the-Flywheel-Command-Line-Interface-CLI-) installed. You will need to log into the CLI with your API key (see your Flywheel user profile - run the command `fw login <API key>`).

#### For running fMRI analyses:
- directory with fmriprep output named 'fmriprep' (see Directory Structure below)
  - func directories (with preprocessed functional files) should be in the subject folder (if there are no sessions) or in the appropriate session folder
  - anat directories (with preprocessed anatomical files) can be in the subject folder or in the appropriate session folder
- EV files (see step 1 below)
- model parameters must be specified in the model_params.json file under the 'model-\<modelname>' directory (see step 2 below)
- condition key must be specified under the 'model-\<modelname>' directory as condition_key.json or condition_key.txt (see step 3 below)
- task contrasts (not required) may be specified under the 'model-\<modelname>' directory as task_contrasts.json or task_contrasts.txt (see step 4 below)

## Steps

#### For downloading data from Flywheel:
1. Run manage_flywheel_downloads.py, which will ask you to specify which data folders/analysis outputs to download, etc. via the command line.
2. Run rm_fmriprep_ses_directories.py if Flywheel adds unwanted session directories to fmriprep outputs.

#### For running fMRI analyses:
1. Run setup.py to create the model directory and all necessary sub-directories. At this stage of the pipeline, if "noconfound" is set to False (because the user would like confound modeling), this setup.py script will generate a confounds.json file that lists all confounds that can be included (this list is pulled from *_bold_confounds.tsv, *_desc-confounds_regressors.tsv, or *_desc-confounds_timeseries.tsv from the fmriprep output). This should make it easier for the user to select which confounds to include in the model. Alternatively, confounds.json can be created manually. If "noconfound" is False, the confounds files are generated (in the onsets directories) on the fly when run_level1.py is called. The user can choose to modify the parameters in model_params.json here via the command line or by editing the json file manually in Step 2. This script will also create empty/sample *.json files (model_params.json, condition_key.json, task_contrasts.json) and onset directories for the EV files.  
   - Example confounds.json:
        ```
        {
                "confounds": [
                    "X", 
                    "Y", 
                    "Z", 
                    "RotX", 
                    "RotY", 
                    "RotZ"
                ]
        }
        ```
3. Modify model_params.json under the 'model-\<modelname>' directory if needed; see explanations for each parameter abbreviation below.  
4. Fill out condition_key.json under the 'model-\<modelname>' directory. The keys are the task names and the values are json objects with EV numbers as keys (formatted as strings) and the condition names as values. (Note: The EV files, *_ev-00\<N>, are always padded with leading zeros so that there are 3 digits.)
   - Example condition_key.json:
        ```
        {
                "flanker":
                        {
                                "1":"congruent_correct",
                                "2":"congruent_incorrect",
                                "3":"incongruent_correct",
                                "4":"incongruent_incorrect"
                        } 
        }
        ```
5. If you need to specify task contrasts, fill out task_contrasts.json. The keys should be the task names and the values should be json objects where the keys are the names of the contrasts and the values are lists that represent the contrast vectors. If you don't want to specify task contrasts for this model, remove this json file.
   - Example task_contrasts.json:
        ```
        {
                "flanker":
                        {
                                "incongruent_vs_congruent":[-1,-1,1,1],
                                "incorrect_vs_correct":[-1,1,-1,1],
                                "incongruent_vs_congruent_correct":[-1,0,1,0],
                                "incorrect_vs_correct_incongruent":[0,0,-1,1]
                        }
        }
        ```   
6. Create the EV files, which belong in the 'onsets' directories in each run folder. Make sure the EV files are named correctly (see the diagram below). Confound files should be saved in the same location as the EV files (the file name ends in *_ev-confounds, see below). (Note that the confounds files can be generated automatically, as mentioned in Step 1.)
7. If customization of fsf files is desired, create a custom stub file named design_level\<N>_custom.stub under the model directory with feat settings (see design_level1_fsl5.stub for examples). If a setting in the custom file is found in the default stub file, the custom setting will replace the existing setting. If the custom setting is not found in the default stub file, it will be added to the fsf.
8. To run a level 1 analysis, use run_level1.py, which will create a job array where each job generates a *.fsf file for a single run and calls the feat command on that fsf file. (By default, if the argument specificruns is not specified, fsf's will be created for all runs.) It may be useful to open one or two *.fsf files using the Feat_gui (locally, not on a cluster) to check that everything has loaded properly, and that the design matrix is as specified.
9. Level 2 and level 3 scripts (run_level2.py, run_level3.py) are run similarly. Use the -h option to see explanations of the parameters.

## Directory Structure
- Session directories are optional. If there aren't multiple sessions, omit the session label from EV file names.
```
basedir
│
└───<studyid>
    │
    └───raw
    │
    └───freesurfer
    │
    └───fmriprep
    │	│
    │	└───anat (can have preprocessed data here or below, under ses-<sesname>)
    │	│
    │	└───ses-<sesname>
    │	    │
    │	    └───anat (can have preprocessed data here)
    │	    │
    │	    └───func (has preprocessed data)
    │
    └───model
        │
        └───level<N>
	    │
	    └───model-<modelname>
	    	│   model_params.json
		│   condition_key.json
		│   task_contrasts.json (optional)
		|   design_level<N>_custom.stub (optional)
	    	│
		└───sub-<subid>
		    │
		    │
		    └───ses-<sesname>
			│
		        └───task-<taskname>_run-<runname>
			    │
			    └───onsets
			        │   sub-<subid>_ses-<sesname>_task-<taskname>_run-<runname>_ev-00<N> (can be .txt or .tsv file) 
			        |   sub-<subid>_ses-<sesname>_task-<taskname>_run-<runname>_ev-confounds (can be .txt or .tsv file) 
			        │
	
```

## Explanations of input parameters
- **studyid**: name of the parent directory of the fmriprep directory
- **basedir**: full path of the grandparent directory of the fmriprep directory (don't include studyid here)
- **sub**: subject identifier (not including the prefix 'sub-')
- **modelname**: name of model (string)
- **taskname**: name of task
- **runname**: name of run
- **smoothing**: mm FWHM; default is 0
- **use_inplane**: use inplane image; default is 0
- **nohpf**: turn off high pass filtering 
- **nowhite**: turn off prewhitening
- **noconfound**: omit motion/confound modeling
- **anatimg**: anatomy image (should be _brain)
- **doreg**: do registration
- **spacetag**: space tag for prepreprocessed data (if the functional or anatomical data was preprocessed in multiple spaces, you can specify the space here) (the script will tell you if multiple preprocessed files were found and thus whether you need to specify this tag)
- **usebrainmask**: apply brain mask to *_preproc.nii.gz by running fslmaths's -mas on *_brainmask.nii.gz and set output to *_preproc_brain.nii.gz. Instead of setting "feat_files(1)" in .fsf to *_preproc.nii.gz, set the output name to *_preproc_brain_nii.gz. If "nofeat" is True, the .fsf will point to *_preproc_brain_nii.gz for "feat_files(1)" but will not create *_preproc_brain_nii.gz. fslmaths's -mas will only be called when feat is also being run
- **callfeat**: (option for mk_level1_fsf.py and mk_level2_fsf.py) automatically calls feat on the *.fsf file that is created by the script
- **specificruns**: JSON object in a string that details which runs to create fsf's for. If specified, ignores specificruns specified in model_params.json. Ex: If there are sessions: '{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}' where flanker is a task name and ["1", "2"] is a list of the runs. If there aren't sessions: '{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}'. Make sure this describes the fmriprep folder, which should be in BIDS format. Make sure to have single quotes around the JSON object and double quotes within.
- **nofeat**: (option for run_level1.py, run_level2.py, get_level1_jobs.py, get_level2_jobs.py, mk_all_level3_fsf.py) don't run feat the *.fsf files 

## Notes on file types
- The EV files can be *.tsv or *.txt files. Just make sure the file is named according to the specification above and that each column is separated by tabs.
- You can check that the json files are formatted properly using this [json formatter](https://jsonformatter.org/).

## Some behaviors to note
- If some feat directories already exist, warnings will be printed. Existing feat directories are never overwritten, but run_level\<N>.py includes an option to remove existing feats. 
- If "specificruns" isn't specified through the command line, "specificruns" from model_params.json is used. If "specificruns" in model_params.json is empty, then the script is run on all runs for all tasks for all subjects (based on the fmriprep directory structure).
- Re: downloading and exporting data from flywheel - if the subject folder for fmriprep/reports/freesurfer does not exist, the entire analysis output for that subject will be downloaded. If the subject folder does exist, only the session folder will be moved to the subject directory. (For freesurfer, however, only one session will be downloaded. There are no session folders in the subject-level freesurfer directories.)
- During level 2 analyses, if registration was not run during the level 1 analysis (as is likely the case if fmriprep was used to preprocess the data), a workaround described [here](https://mumfordbrainstats.tumblr.com/post/166054797696/feat-registration-workaround) is performed so that the level 2 analysis does not automatically fail.
- During level 3 analyses, subjects are by default pulled from the fmriprep folder (I should probably modify this at some point in the future so that it pulls the subjects specified in model_params.json). However, you can specify which subjects to include using the `--subs` argument of run_level3.py.

## Miscellaneous notes
- TR is obtained by reading the header of the Nifti file (preproc func file)
