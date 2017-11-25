


## Install Python 3 virtualenv

  $ sudo apt-get install python3-venv

## Initialize and activate the virtual environment:

    $ pyvenv venv
    $ . ./venv/bin/activate
    $ pip install pip --upgrade

## Running

    # source some variables
    $ set -a
    $ . ENV
    $ set +a

    $ FLASK_APP=tourmap/app.py flask run --reload --without-threads -h 0.0.0.0 --eager-loading
