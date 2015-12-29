#!/bin/bash

# docker run -ti --name wsgi -p 127.0.0.1:80:8000 --link mysql_db 5f2208aba54f /bin/bash

function clean_container {
    echo "Clean test ..."
    names="^(mysql_db|wsgi)$"
    docker ps --format "{{.Names}}" -f status=running | grep -P "$names" | xargs -I % docker stop %
    docker ps --format "{{.Names}}" -f status=exited | grep -P "$names" | xargs -I % docker rm %
    rm -rf build
}

echo 'Build msf...'
mkdir -p build/msf
cp -r ../../../msf ../../../setup.py build/msf
cd build
tar -caf msf.tar.gz msf
cd ../

echo 'Build demo wsgi application...'
cp -r ../../../demo build/
cd build
tar -caf demo.tar.gz demo
cd ../

docker run --name mysql_db -d -P -e MYSQL_ROOT_PASSWORD=root_password -e MYSQL_DATABASE=wsgi_database -e MYSQL_USER=wsgi_user -e MYSQL_PASSWORD=wsgi_password  mysql:5.7
if [ $? != 0 ]; then 
    clean_container
    exit 1;
else
    echo "mysql_db running"
fi

output=$(mktemp)
echo 'Create tmp file' $output


docker build . > "$output"
if [ $? != 0 ]; then 
    rm $output
    clean_container
    exit 1
else
    echo "WSGI built"
fi

wsgi_img_id=$(grep "Successfully built" "$output" | cut -d ' ' -f 3)

mysql_port=$(docker inspect --format '{{ (index (index .NetworkSettings.Ports "3306/tcp") 0).HostPort }}'  mysql_db)
sleep 6

docker run --name wsgi -p 127.0.0.1:80:8000 --link mysql_db $wsgi_img_id &
if [ $? != 0 ]; then
    rm $output
    clean_container
    exit 1;
else
    echo "WSGI running"
fi

sleep 6
python3 -m unittest test
exit_status=$?
clean_container
exit $exit_status

