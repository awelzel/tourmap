tourmapp - show multiple Strava rides on a single map


# Running

## Install Python 3 virtualenv

    # On Debian
    $ sudo apt-get install python3-venv

## Initialize, activate and populate a venv

    $ pyvenv venv
    $ . ./venv/bin/activate
    $ pip install pip --upgrade
    $ pip install -r ./requirements.txt

## Run tests

    $ python -m unittest discover tourmap_test/

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
