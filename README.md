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



## The ``public`` flag:

The only effect of an unset ``public`` flag is that this tour will not be
listed in the Public Tours section. And that's it. Anyone who has a direct
link to the tour can visit and see it.
