.. _entrypoint:


**********
EntryPoint
**********

import::

    from woof.url import EntryPoint


The EntryPoint is used to bind at an **URL pattern** a controller. An **URL pattern** is 
list of word separate by /. 

i.e:
    /foo/bar

When you instanciate an EntryPoint you can define a string wich will prefix each URL pattern.:

:
    root_url = EntryPoint("/api")


A word may be a substitution word when it is surrounded by braces. When an URL is search in 
the EntryPoint object, a substitution word in URL pattern will be replaced by word in URL.
If the URL matches an URL pattern the bound controller is returned with the replaced words.

i.e:
    This URL pattern /foo/{bar}/toto match the URL /foo/pink/toto


