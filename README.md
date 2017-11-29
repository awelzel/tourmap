

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

    $ FLASK_APP=tourmap/app.py flask run --reload -h 0.0.0.0 --eager-loading

## Database new tables

    $ FLASK_APP=tourmap/app.py flask createdb
    $ FLASK_APP=tourmap/app.py flask resetdb
