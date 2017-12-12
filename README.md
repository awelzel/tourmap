

## Install Python 3 virtualenv

  $ sudo apt-get install python3-venv

## Initialize and activate the virtual environment:

    $ pyvenv venv
    $ . ./venv/bin/activate
    $ pip install pip --upgrade

## Running the server

    # source some variables
    $ set -a
    $ . ENV
    $ set +a

    $ FLASK_APP=tourmap/app.py flask run --reload -h 0.0.0.0 --eager-loading --with-threads

## Database new tables

    $ FLASK_APP=tourmap/app.py flask createdb
    $ FLASK_APP=tourmap/app.py flask resetdb

## The ``public`` flag:

The only effect of an unset ``public`` flag is that this tour will not be
listed in the Public Tours section. And that's it. Anyone who has a direct
link to the tour can visit and see it.
