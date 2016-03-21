.. _controllers:


***********
Controllers
***********

A controller is callable which must return a resource instance when is bound with post, put or get single URL.
When a controller is bound with get list URL, it must return a Query object and None with delete URL.
It take a body extra parameters with post and put URL.


    +-----------+--------------------+-----------------------------+
    |URL Verbe  |  Parameters        | Return                      |
    +-----------+--------------------+-----------------------------+
    |GET single | take in url        | A Resource object           |
    +-----------+--------------------+-----------------------------+
    |GET list   | take in url        | A Query object              |
    +-----------+--------------------+-----------------------------+
    | POST      | body + take in url | A Resource object           |
    +-----------+--------------------+-----------------------------+
    | PUT       | body + take in url | A Resource object           |
    +-----------+--------------------+-----------------------------+
    | DELETE    | take in url        | None                        |
    +-----------+--------------------+-----------------------------+

