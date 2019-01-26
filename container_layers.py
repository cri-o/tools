#!/usr/bin/env python

import json
import os
import re
import subprocess
import sys


class SearchError(Exception):
    pass

class ContainerStateError(Exception):
    pass


def get_container_layers(id):
    try:
        container_status = subprocess.check_output(
            ["runc", "state", container_id])
    except subprocess.CalledProcessError as e:
        print "runc state failed: ", e.output
        raise ContainerStateError("container not found or invalid container id")

    status_json = json.loads(container_status)
    if status_json['status'] == "stopped":
        raise ContainerStateError("container already stopped")

    rootfs_path = status_json['rootfs']
    dir_path = os.path.dirname(rootfs_path)
    top_layer_id = os.path.basename(dir_path)
    container_pid = status_json['pid']

    # Note: os.path.join failed for some reason on RHCOS
    container_mounts_path = "/proc/" + str(container_pid) + "/mountinfo"
    container_mount_output = ""
    with open(container_mounts_path, "r") as f:
        for line in f:
            if re.search(top_layer_id, line):
                container_mount_output = line
                break

    if container_mount_output == "":
        raise SearchError("container mount not found; probably exited")

    layers = []
    m = re.search('lowerdir=(.*),upperdir', container_mount_output)
    if m:
        lower_dirs = m.group(1).split(':')
        for l in lower_dirs:
            layers.append(l)
    else:
        raise SearchError("Unable to find lowerdir in mount output: ", container_mount_output)

    m = re.search('upperdir=(.*),workdir', container_mount_output)
    if m:
        upper_dir = m.group(1)
        layers.append(upper_dir)
    else:
        raise SearchError("Unable to find upperdir in mount output: ", container_mount_output)

    return layers


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: sys.argv[0] <container_id>"
        sys.exit(1)

    container_id = sys.argv[1]
    try:
        layers = get_container_layers(container_id)
    except Exception as e:
        print "Getting container layers failed: ", e
        sys.exit(1)
    else:
        for l in layers:
            print l
