#!/bin/bash
. venv/bin/activate
python3 -m unittest discover -s tourmap_test/ -v $*
