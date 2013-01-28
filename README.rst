
Ureport_Project
========================

Below you will find basic setup instructions for the ureport_project
project. To begin you should have the following applications installed on your
local development system:

- Python >= 2.6 (2.7 recommended)
- `pip >= 1.1 <http://www.pip-installer.org/>`_
- `virtualenv >= 1.8 <http://www.virtualenv.org/>`_

Getting Started
---------------

To setup your local environment you should create a virtualenv and install the
necessary requirements::

    virtualenv --distribute ureport_project-env
    source ureport_project-env/bin/activate
    cd ureport_project
    pip install -r requirements/base.txt
    pip install -r requirements/requires.txt

    git submodule update --init
Run syncdb::

    python manage.py syncdb
    python manage.py migrate

You should now be able to run the development server::

    python manage.py runserver
