#!/bin/bash
gunicorn -w 4 -b 0.0.0.0:5000 --certfile=pythoncert.pem --keyfile=pythonkey.pem app:create_app
