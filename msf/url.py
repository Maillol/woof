#!/usr/bin/env python3


class _PathParameter:
    """
    Substitution sting in path
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'P({})'.format(self.name)



class URLPathTree:
    """
    Store path template.

    A path template is string wich contains one or several word
    separate by the '/' char. A word can be a substitution sting if it surrounded by braces.

    i.e:
        This path template:
            /hotel/{hotel_name}/rooms/{room_id}
        
        matches this path: 
            /hotel/california/room/43
    """

    class Node:
        def __init__(self, value, ctrl=None):
            self.value = value
            self.children = ()
            self.ctrl = ctrl

    def __init__(self):
        self._root = URLPathTree.Node('')

    def add(self, url, ctrl):
        """
        Assigne ctrl to a url in the tree.
        """
        current_node = self._root
        for url_dir in url.split('/')[1:]:
            if url_dir.startswith('{'):
                url_dir = _PathParameter(url_dir)
            for child in current_node.children:
                if child.value == url_dir:
                    current_node = child
                    break
            else:
                new_node = URLPathTree.Node(url_dir)
                current_node.children += (new_node,)
                current_node = new_node
        current_node.ctrl = ctrl

    def get(self, url):
        """
        Search url in the tree and a 2-tuple wich contains ctrl 
        and list of parameters. If url isn't found LookupError is raised
        with url in args[1]
        """
        def walk(path, node, values):
            if not path:
                return node.ctrl, values

            for node in node.children:
                if isinstance(node.value, _PathParameter):
                    result = walk(path[1:], node, values + path[:1])
                    if result is not None:
                        return result
                elif node.value == path[0]:
                    result = walk(path[1:], node, values)
                    if result is not None:
                        return result

        path = url.split('/')
        result = walk(path[1:], self._root, [])
        if result is None:
            raise LookupError("URL not found", url)
        return result

    def __repr__(self):
        def walk(node, offset):
            out = ' ' * (offset * 4)
            out += '({n.value}, {n.ctrl})\n'.format(n=node)
            for child in node.children:
                out += walk(child, offset + 1)
            return out
        return walk(self._root, 0)


class EntryPoint:
    """
    Define REST API entry points.

    1) Define path to your REST API.

        root = EntryPoint('/api')

    2) Define path to each resource.

        @root.get('/hotel/{hotel_id}')
        def get_hotel(hotel_id):
            return Hotel.select().where(Hotel.id == hotel_id)
    """

    def __init__(self, url_prefix=''):
        self.url_prefix = url_prefix
        self.get_urls = URLPathTree()
        self.put_urls = URLPathTree()
        self.post_urls = URLPathTree()
        self.del_urls = URLPathTree()
        self.opt_urls = URLPathTree()

    def get(self, url, **kwargs):
        """
        Return decorator to link URL with get method to controller
        """
        def decorator(ctrl):
            self.get_urls.add(url, ctrl)
            for key, value in kwargs.items():
                ctrl.key = value
            return ctrl
        return decorator

    def put(self, url):
        """
        Return decorator to link URL with put method to controller
        """
        def decorator(ctrl):
            self.put_urls.add(url, ctrl)
            return ctrl
        return decorator

    def post(self, url):
        """
        Return decorator to link URL with post method to controller
        """
        def decorator(ctrl):
            self.post_urls.add(url, ctrl)
            return ctrl
        return decorator

    def delete(self, url):
        """
        Return decorator to link URL with delete method to controller
        """
        def decorator(ctrl):
            self.del_urls.add(url, ctrl)
            return ctrl
        return decorator

