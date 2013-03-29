ureport-project
===============

new ureport based on the latest rapidsms 0.13.0 and github.com/nyaruka's httprouter

To setup
--------

    git clone https://github.com/unicefburundi/ureport-project.git ureport_project
    cd ureport_project
    git submodule update --init
    python manage.py syncdb
    python manage.py migrate #this throws some errors at the moment
    python manage.py migrate rapidsms_httprouter
    python manage.py migrate poll
    python manage.py migrate rapidsms_script
    python manage.py migrate rapidsms_xforms
    python manage.py migrate

