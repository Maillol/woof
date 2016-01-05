#!/bin/bash

cd demo

echo '{"database": ' \
         '{"provider": "mysql", ' \
         '"host": "'$MYSQL_DB_PORT_3306_TCP_ADDR'", ' \
         '"port": '$MYSQL_DB_PORT_3306_TCP_PORT', ' \
         '"password" : "'$MYSQL_DB_ENV_MYSQL_PASSWORD'", '\
         '"database": "'$MYSQL_DB_ENV_MYSQL_DATABASE'", '\
         '"user": "'$MYSQL_DB_ENV_MYSQL_USER'"}' \
     '}' > config.json

woof createdb demo --py-path $PWD

python3 -c "from wsgiref.simple_server import make_server; \
            from wsgi import application; \
            make_server('', 8000, application).serve_forever()"
