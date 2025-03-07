#! /usr/bin/env python3
"""Create a python script to re-run a job given the job ID for a gear that was run on Flywheel."""

import argparse
import os
import pprint
import stat

import flywheel


def get_container_path(fw, group_id, project_label, destination):
    """Get path to container that can be found by fw.lookup()."""

    container_path = "Invalid"
    subject = None
    session = None

    if isinstance(destination, flywheel.models.project_output.ProjectOutput):
        container_path = f"{group_id}/{project_label}"

    elif isinstance(destination, flywheel.models.subject_output.SubjectOutput):
        container_path = f"{group_id}/{project_label}/{destination.label}"

    elif isinstance(destination, flywheel.models.session_output.SessionOutput):
        container_path = (
            f"{group_id}/{project_label}/{destination.subject.label}/"
            + f"{destination.label}"
        )

    elif isinstance(destination, flywheel.models.acquisition_output.AcquisitionOutput):
        subject = fw.get_subject(destination.parents.subject)
        session = fw.get_session(destination.parents.session)
        container_path = (
            f"{group_id}/{project_label}/{subject.label}/{session.label}/"
            + f"{destination.label}"
        )

    elif isinstance(destination, flywheel.models.analysis_output.AnalysisOutput):

        if destination.parent.type == "project":
            container_path = f"{group_id}/{project_label}/analyses/{destination.label}"

        elif destination.parent.type == "subject":
            subject = fw.get_subject(destination.parents.subject)
            container_path = f"{group_id}/{project_label}/{subject.label}/analyses/{destination.label}"

        elif destination.parent.type == "session":
            subject = fw.get_subject(destination.parents.subject)
            session = fw.get_session(destination.parents.session)
            container_path = (
                f"{group_id}/{project_label}/{subject.label}/{session.label}/analyses/{destination.label}"
            )
        else:
            print(f"Error: unexpected destination parent type {type(destination.parent.type)}")

        # analyses often have names with / in them, so add "analysis " to
        # indicate to search analyses to find one with the right file name
        if "/" in destination.label:
            chop_len = len(container_path) - len(destination.label) - 10
            container_path = "analysis " + container_path[:chop_len]
            print(f"Found / in destination label using:\n   {container_path}\n")

    else:
        print(f"Error: unexpected destination type {type(destination)}")

    return container_path


def main(job_id):

    fw = flywheel.Client("")
    print("Flywheel Instance", fw.get_config().site.api_url)

    analysis = None
    if args.analysis:
        analysis = fw.get_analysis(job_id)
        print(f"Getting job_id from analysis '{analysis.label}'")
        job_id = analysis.job.id

    print("Job ID", job_id)
    job = fw.get_job(job_id)
    gear = fw.get_gear(job.gear_id)
    gear_name = gear.gear.name
    print(f"gear.gear.name is {gear_name}")
    destination_id = job.destination.id
    destination_type = job.destination.type
    print(f"job's destination_id is {destination_id} type {destination_type}")

    if job.destination.type == "analysis":
        analysis = fw.get_analysis(destination_id)
        destination_id = analysis.parent.id
        destination_type = analysis.parent.type
        print(f"job's analysis's parent id is {destination_id} type {destination_type}")

    destination = fw.get(destination_id)
    destination_label = destination.label
    print(f"new job's destination is {destination_label} type {destination_type}")

    group_id = destination.parents.group
    print(f"Group id: {group_id}")

    if destination_type == "project":
        project = destination
    else:
        project = fw.get_project(destination.parents.project)
    project_label = project.label
    print(f"Project label: {project.label}")

    script_name = f"{gear_name}_{destination_type}_{destination.label}.py"
    script_name = script_name.replace(" ", "_")
    print(f"Creating script: {script_name} ...\n")

    container_path = get_container_path(fw, group_id, project_label, destination)

    input_files = dict()
    for key, val in job.config.get("inputs").items():
        if "hierarchy" in val:
            input_container = fw.get(val["hierarchy"]["id"])
            input_container_path = get_container_path(
                fw, group_id, project_label, input_container
            )
            input_files[key] = {
                "container_path": input_container_path,
                "location_name": val["location"]["name"],
            }

    lines = f"""#! /usr/bin/env python3
'''Run {gear.gear.name} on {destination_type} "{destination.label}"

    This script was created to run Job ID {job_id}
    In project "{group_id}/{project_label}"
    On Flywheel Instance {fw.get_config().site.api_url}
'''

import os
import argparse
from datetime import datetime


import flywheel


input_files = {pprint.pformat(input_files)}

def main(fw):

    gear = fw.lookup("gears/{gear.gear.name}")
    print("gear.gear.version in original job was = {gear.gear.version}")"""

    sfp = open(script_name, "w")
    for line in lines.split("\n"):
        sfp.write(line + "\n")

    sfp.write('    print(f"gear.gear.version now = {gear.gear.version}")\n')
    sfp.write(f'    print("destination_id = {destination_id}")\n')
    sfp.write(f'    print("destination type is: {destination_type}")\n')

    sfp.write(f'    destination = fw.lookup("{container_path}")\n')

    sfp.write("\n")
    sfp.write("    inputs = dict()\n")
    sfp.write("    for key, val in input_files.items():\n")
    sfp.write("         if val['container_path'][:8] == 'analysis':\n")
    sfp.write("             path = val['container_path'][9:]\n")
    sfp.write("             parent_of_analysis = fw.lookup(path)\n")
    sfp.write("             # find analysis that has the right file\n")
    sfp.write("             analyses = parent_of_analysis.reload().analyses\n")
    sfp.write("             for analysis in analyses:\n")
    sfp.write("                 for file in analysis.files:\n")
    sfp.write("                     if file.name == val['location_name']:\n")
    sfp.write("                         container = analysis\n")
    sfp.write("         else:\n")
    sfp.write("             container = fw.lookup(val['container_path'])\n")
    sfp.write("         inputs[key] = container.get_file(val['location_name'])\n")
    sfp.write("\n")
    sfp.write(f"    config = {pprint.pformat(job['config']['config'], indent=4)}\n")
    sfp.write("\n")
    tags = job["tags"]
    if "analysis" in tags:
        tags.remove("analysis") # that will be added automatically
    sfp.write(f"    tags = {pprint.pformat(tags, indent=4)}\n")
    sfp.write("\n")

    if job.destination.type == "analysis":
        sfp.write("    now = datetime.now()\n")
        sfp.write("    analysis_label = (\n")
        sfp.write(
            "        f'{gear.gear.name} {now.strftime(\"%m-%d-%Y %H:%M:%S\")} SDK launched'\n"
        )
        sfp.write("    )\n")
        sfp.write("    print(f'analysis_label = {analysis_label}')\n")

        lines = f"""
    analysis_id = gear.run(
        analysis_label=analysis_label,
        tags=tags,
        config=config,
        inputs=inputs,
        destination=destination,
    )"""
        for line in lines.split("\n"):
            sfp.write(line + "\n")
        sfp.write("    print(f'analysis_id = {analysis_id}')\n")
        sfp.write("    return analysis_id\n")

    else:
        lines = f"""
    job_id = gear.run(
        tags=tags,
        config=config,
        inputs=inputs,
        destination=destination
    )"""
        for line in lines.split("\n"):
            sfp.write(line + "\n")
        sfp.write("    print(f'job_id = {job_id}')\n")
        sfp.write("    return job_id\n")

    lines = f"""
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()

    fw = flywheel.Client('')
    print(fw.get_config().site.api_url)

    analysis_id = main(fw)"""

    for line in lines.split("\n"):
        sfp.write(line + "\n")

    sfp.write("\n")
    sfp.write("    os.sys.exit(0)\n")

    sfp.close()

    try:
        os.system(f"black {script_name}")
    except Exception:
        print("black not found, skipping formatting")

    st = os.stat(script_name)
    os.chmod(script_name, st.st_mode | stat.S_IEXEC)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("job_id", help="Flywheel job ID")
    parser.add_argument(
        "-a",
        "--analysis",
        action="store_true",
        help="ID provided is for the analysis (job destination)",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0)

    args = parser.parse_args()

    main(args.job_id)

    os.sys.exit(0)
