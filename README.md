# Another Web Scrapper #

## Install ##

### Debian 7 ###

Install dependencies:

    #sudo aptitude install python-virtualenv ipython python-lxml python-crypto python-unidecode python-qt4 libqt4-webkit libqt4-core libqt4-gui libqt4-dev qt4-qmake xvfb
    sudo aptitude install python-pyside.qtwebkit python-virtualenv ipython python-lxml python-crypto python-unidecode xvfb git

For sqlite3:

    sudo aptitude install python-pysqlite2 sqlite3

For postgres:
    sudo aptitude install  python-psycopg2

Then checkout repository and initialize environment:

    git clone https://pborky@bitbucket.org/pborky/scrap.git
    cd scrap
    make initenv
    bin/activate
    make dev-setup

You will be asked for administrator user name and password.

Now you are ready to start server and enjoy:

    sudo -u www-data  xvfb-run -a bin/python manage.py runserver 0.0.0.0:8000

#### Setup apache and mod-wsgi ####

    sudo aptitude install apache2 libapache2-mod-wsgi


