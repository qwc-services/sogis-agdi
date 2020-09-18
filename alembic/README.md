Migrations for ConfigDB
=======================

Database migrations using [Alembic](http://alembic.zzzcomputing.com/en/latest/)


Setup
-----

Activate virtual environment:

    source env/bin/activate

Install requirements:

    pip install -r requirements.txt

Uses PostgreSQL connection service `soconfig_services` (ConfigDB) (cf. `sqlalchemy.url` in `../alembic.ini`).


Usage
-----

Run commands from root directory.

Create a migration script:

    alembic revision -m "create sample table"

Edit generated migration script `alembic/versions/123456abcdef_create_sample_table.py`

Run migrations:

    alembic upgrade head

Upgrade one version:

    alembic upgrade +1

Downgrade one version:

    alembic downgrade -1
