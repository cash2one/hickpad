#!/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
import py2exe

includes = ["encodings", "encodings.*"]
options = {
    "py2exe":
        {
            "compressed": 1,
            "optimize": 2,
            "includes": includes,
            "bundle_files": 1
        }
    }
data_files = [("ico", ["ico/hickpad.ico"])]

# Hickpad.ico
setup(windows=[{"script": "hickpad.pyw", "icon_resources": [(1, "ico/hickpad.ico")]}], options = options, zipfile = None, data_files = data_files)



