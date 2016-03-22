sudo aptitude install postgresql   python-psycopg2
bin/pip install -r requirements/dev.txt

dd if=/dev/random bs=1 count=30 2>/dev/null | base64
sudo -u postgres createuser scrap --no-createdb --encrypted --pwprompt --no-createrole --no-superuser
sudo -u postgres psql <<-EOF
CREATE DATABASE scrap_dev OWNER = scrap ENCODING = 'UNICODE';
EOF

python manage.py dumpdata --indent=4  -e contenttypes -e sessions  --database=lite project > tmp/project_fixture.json
python manage.py dumpdata --indent=4  -e contenttypes -e sessions  --database=lite app > tmp/app_fixture.json
python manage.py dumpdata --indent=4  --database=lite auth contenttypes > tmp/auth_fixture.json

rm **/migrations -fr
python manage.py schemamigration project --initial
python manage.py schemamigration app --initial
python manage.py migrate project  --fake --database=lite --delete-ghost-migrations
python manage.py migrate app --fake --database=lite --delete-ghost-migrations

python manage.py datamigration project newdb
python manage.py datamigration app newdb

sed -i '/def\s\+forwards/,+3d' **/migrations/0002_newdb.py
cat >> project/migrations/0002_newdb.py <<-EOF
    def forwards(self, orm):
        from django.core.management import call_command
        call_command("loaddata", "tmp/auth_fixture.json")
        call_command("loaddata", "tmp/project_fixture.json")
EOF
cat >> app/migrations/0002_newdb.py <<-EOF
    def forwards(self, orm):
        from django.core.management import call_command
        call_command("loaddata", "tmp/app_fixture.json")
EOF

python manage.py syncdb --noinput
python manage.py migrate

