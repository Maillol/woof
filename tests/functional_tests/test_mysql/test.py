import unittest
import subprocess
import requests
import json

TEMPLATE = '{{(index (index .NetworkSettings.Ports "3306/tcp") 0).HostPort}}'
#MYSQL_PORT = subprocess.check_output(['docker', 'inspect',
#                                      '--format', TEMPLATE, 'mysql_db'])
#MYSQL_PORT = int(MYSQL_PORT.strip())
WSGI_PORT=80
URL = "http://127.0.0.1:{}/api".format(WSGI_PORT)


class TestCrud(unittest.TestCase):
    def test_001_create_hotel(self):
        hotel = dict(name="Koalas", address="45 horse street")
        response = requests.post(URL + "/hotels", json=hotel)
        hotel.update(dict(id=1, rooms=[]))
        self.assertEqual(response.json(), hotel)

    def test_002_select_one_hotel(self):
        expected = dict(id=1, name="Koalas",
                        address="45 horse street", rooms=[])
        response = requests.get(URL + "/hotels/1")
        self.assertEqual(response.json(), expected)

    def test_003_update_hotel(self):
        hotel = dict(name="The horse", address="45 horse street")
        response = requests.put(URL + "/hotels/1", json=hotel)
        hotel.update(dict(id=1, rooms=[]))
        self.assertEqual(response.json(), hotel)

