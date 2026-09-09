# -*- coding: utf-8 -*-
"""
run.py
======
Point d'entree pour lancer le serveur de developpement.
Usage : python run.py
En production, utiliser un serveur WSGI (Gunicorn) : gunicorn run:app
"""

import os

from app import app

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=debug)
