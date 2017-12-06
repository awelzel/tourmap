web: FLASK_APP=tourmap/app.py flask run --with-threads --eager-loading -h 0.0.0.0 -p $PORT
worker: FLASK_APP=tourmap/app.py flask strava_poller
