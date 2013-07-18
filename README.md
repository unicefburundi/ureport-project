ureport-project
===============

new ureport based on the latest rapidsms 0.13.0 and github.com/nyaruka's httprouter

To setup
--------

    git clone https://github.com/unicefburundi/ureport-project.git ureport_project
    cd ureport_project
    pip install -r requirements/base.txt
    pip install -r requirements/requires.txt
    git submodule update --init
    python manage.py syncdb
    python manage.py migrate 

