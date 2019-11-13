#!/usr/bin/env python
import argparse
import multiprocessing
import os
import subprocess
from typing import List
from datetime import datetime

from roster_utils import get_device_list, DeviceInfo, show_status


def copy_calibrations_device(device: DeviceInfo):

    calib_types = ["camera_intrinsic", "camera_extrinsic", "kinematics"]

    return_message = ""

    for calib_type in calib_types:

        OUTPUT_DIR = '../'
        if "autobot" in device.hostname:
            OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'autobots')
        else:
            OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'watchtowers')
            if calib_type != "camera_intrinsic":
                continue

        filename = "/data/config/calibrations/%s/%s.yaml" % (
            calib_type, device.hostname)

        ssh_host = '%s@%s.local' % (device.username, device.hostname)
        cmd = 'ssh %s "if [ -f %s ]; then \
                        exit 0; \
                    else \
                        exit 3; \
                    fi"' % (ssh_host, filename)

        try:
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if e.returncode == 3:
                return_message += "No file for %s " % calib_type
            return "SSH Error"

        date = datetime.today().strftime('%Y-%m-%d')

        folder_sub_name = 'intrinsic-calibration'
        if calib_type == "camera_extrinsic":
            folder_sub_name = 'extrinsic-calibration'
        if calib_type == "kinematics":
            folder_sub_name = 'kinematics'

        OUTPUT_DIR = os.path.join(OUTPUT_DIR, device.hostname,
                                  folder_sub_name, str("%s_%s" % (date, folder_sub_name)))

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        fn = os.path.join(OUTPUT_DIR, "%s.yaml" % device.hostname)

        cmd = 'ssh %s "md5sum %s"' % (ssh_host, filename)

        try:
            md5_before_copy = subprocess.check_output(cmd, shell=True)
            md5_before_copy = (
                md5_before_copy.rstrip().decode("utf-8")).split()[0]
        except subprocess.CalledProcessError:
            return_message += "MD5 error - agent for %s" % calib_type

        cmd = 'scp %s:%s %s' % (ssh_host, filename, fn)

        try:
            res = subprocess.check_output(cmd, shell=True)
            res = res.rstrip().decode("utf-8")
        except subprocess.CalledProcessError:
            return_message += "Copy failed for %s" % calib_type

        cmd = 'md5sum %s' % fn

        try:
            md5_after_copy = subprocess.check_output(cmd, shell=True)
            md5_after_copy = md5_after_copy.rstrip().decode("utf-8").split()[0]
        except subprocess.CalledProcessError:
            return_message += "MD5 error - server for %s" % calib_type

        if md5_after_copy == md5_before_copy:
            return_message += "MD5 matches"
        else:
            os.unlink(fn)
            return_message += "MD5 mismatch for %s" % calib_type

    return return_message


def copy_calibrations_all_devices(device_list: List[DeviceInfo]):
    pool = multiprocessing.Pool(processes=20)
    results = pool.map(copy_calibrations_device, device_list)
    pool.close()
    pool.join()

    show_status(device_list, results)


def copy_calibrations_main():

    device_list = get_device_list('device_list.txt')

    print('Copying calibrations:')
    copy_calibrations_all_devices(device_list)


if __name__ == '__main__':
    copy_calibrations_main()
