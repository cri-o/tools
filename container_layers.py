#!/usr/bin/env python

import json
import os
import re
import subprocess
import sys


def get_container_layers(id):
    try:
        container_status = subprocess.check_output(
            ["runc", "state", container_id])
    except subprocess.CalledProcessError:
        print("container not found; probably exited")
        sys.exit(0)

    status_json = json.loads(container_status)
    if status_json['status'] == "stopped":
        print("container already stopped")
        sys.exit(0)

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
        print("container mount not found; probably exited")
        sys.exit(0)

    layers = []
    m = re.search('lowerdir=(.*),upperdir', container_mount_output)
    if m:
        lower_dirs = m.group(1).split(':')
        for l in lower_dirs:
            layers.append(l)
    else:
        print("Unable to find lowerdir in mount output: ", container_mount_output)
        sys.exit(1)

    m = re.search('upperdir=(.*),workdir', container_mount_output)
    if m:
        upper_dir = m.group(1)
        layers.append(upper_dir)
    else:
        print("Unable to find upperdir in mount output: ", container_mount_output)
        sys.exit(1)

    return layers


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sys.argv[0] <container_id>")
        sys.exit(1)

    container_id = sys.argv[1]
    layers = get_container_layers(container_id)
    for l in layers:
        print(l)
