#!/usr/bin/env python2
"""
Patch the HSM config file to set correct settings for use with a Vagrant
development setup.

Note: this used to be a simple patch file but since the format changed, it
seems better to parse the file, change the json object and dump it back to the
file.
"""
import simplejson as json
import yaml
import sys
import os.path

MAX_RECURSION = 100

PATCHES = {
    "test/config/va.json": {
        "va": {
            "portConfig": {
                "httpPort": 80,
                "httpsPort": 443
            }
        }
    },
    "test/rate-limit-policies.yml": {
        "certificatesPerName": {
            "threshold": 1000
        },
        "certificatesPerFQDNSet": {
            "threshold": 1000
        }
    },
    "test/test-ca.key-pkcs11.json": {
        "module": "/usr/lib/softhsm/libsofthsm.so",
    }
}


def recursive_update(old_obj, new_obj, depth=0):
    if depth > MAX_RECURSION:
        raise RuntimeError("Maximum recursion level reached.")

    if isinstance(new_obj, dict):
        for key, value in new_obj.items():
            old_obj[key] = recursive_update(
                old_obj[key], new_obj[key], depth+1)
    elif isinstance(new_obj, (list, tuple)):
        # Merge lists/tuples.
        old_obj = old_obj + new_obj
    else:
        # Set strings, integers, etc. and set() so arrays can be
        # overridden.
        old_obj = new_obj
    return old_obj


def patch_yaml(file, obj):
    with open(file, "r") as fp:
        yaml_obj = yaml.load(fp)
        yaml_obj = recursive_update(yaml_obj, obj)
    with open(file, "w") as fp:
        yaml.dump(yaml_obj, fp, default_flow_style=False)


def patch_json(file, obj):
    with open(file, "r") as fp:
        json_obj = json.load(fp)
        json_obj = recursive_update(json_obj, obj)
    with open(file, "w") as fp:
        json.dump(json_obj, fp, indent=4)


if __name__ == '__main__':
    try:
        for patch_file, patch_obj in PATCHES.items():
            _, file_extension = os.path.splitext(patch_file)
            if file_extension in (".yml", ".yaml"):
                patch_yaml(patch_file, patch_obj)
            elif file_extension in (".json", ".js"):
                patch_json(patch_file, patch_obj)
            else:
                raise NotImplementedError(
                    "Can't patch files with %s extension" % file_extension)
            print("Patched {}".format(os.path.abspath(patch_file)))

    except (OSError, IOError), exc:
        print(
            "Failed to patch the HSM for development, reason: {}".format(exc))
        sys.exit(1)
