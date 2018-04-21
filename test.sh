#!/bin/bash
. venv/bin/activate
coverage run --include='tourmap/*' -m unittest discover -s tourmap_test/ -v $*
