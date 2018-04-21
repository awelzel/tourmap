# tourmapp

[![Build Status](https://travis-ci.org/awelzel/tourmapp.svg?branch=master)](https://travis-ci.org/awelzel/tourmapp)

Show multiple Strava rides on a single map.

A demo is running at https://tourmapp.herokuapp.com


# Running

## Initialize, activate and populate a Python 3 virtualenv

    $ pyvenv venv
    $ . ./venv/bin/activate
    $ pip install pip --upgrade
    $ pip install -r ./requirements.txt

## Run some tests

    $ ./test.sh

## Install js/css stuff (jquery, bootstrap, leaflet)

    $ npm install

## Create a config file

    $ cp config.py.template config.py
    # Update config settings...
    $ vim config.py

## Create the database tables

    $ FLASK_APP=tourmap/app.py flask createdb

## Run the flask server

    $ FLASK_APP=tourmap/app.py flask run --reload -h 0.0.0.0 \
        --eager-loading --with-threads


## Running the strava_poller process

This process fetches activities from Strava users that logged through with
their Strava credentials.

    $ . venv/bin/activate
    $ FLASK_APP=tourmap/app.py flask strava_poller

The way it currently fetches Strava activities should work for a few users,
but may need to be reworked when many users log in.

# Sample Images

## Overview of a tour
![Zoomed-out](img/zoomout.png?raw=true)

## Zoomed-in with popup
![Zoomed-in and expanded popup](img/zoomin.png?raw=true)
