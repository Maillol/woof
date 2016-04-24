#!/usr/bin/env python3

import inspect


class _PathParameter:
    """
    Substitution sting in path
    """

    def __init__(self, name):
        self.name = name[1:-1]

    def __repr__(self):
        return 'P({})'.format(self.name)



class URLPathTree:
    """
    Store path template.

    A path template is string which contains one or several word
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

        def __repr__(self):
            return ("<Node ('{s.value}', {s.ctrl}, {nb_children})>"
                    .format(s=self, nb_children=len(self.children)))

    def __init__(self):
        self._root = URLPathTree.Node('')

    @staticmethod
    def _validate_ctrl(ctrl, url):
        try:
            argspec = inspect.getfullargspec(ctrl)
        except TypeError:
            raise TypeError("{} isn't callable".format(ctrl))

        if argspec.varkw is None:
            if argspec.args and argspec.args[0] == 'self':
                del argspec.args[0]

            for word in url.split('/'):
                if word.startswith('{'):
                    if word[1:-1] not in argspec.args:
                        raise TypeError("{} must have '{}' argument"
                                        .format(ctrl, word[1:-1]))

    def add(self, url, ctrl):
        """
        Assigne ctrl to a url in the tree.
        """

        try:
            found_ctrl, _ = self.get(url)
        except LookupError:
            pass
        else:
            raise ValueError("URL '{}' already linked with {}"
                             .format(url, found_ctrl))

        self._validate_ctrl(ctrl, url)

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
                if node.ctrl is None:
                    return None
                return node.ctrl, values

            for node in node.children:
                if isinstance(node.value, _PathParameter):
                    result = walk(path[1:], node, values)
                    if result is not None:
                        values[node.value.name] = path[0]
                        return result

                elif node.value == path[0]:
                    result = walk(path[1:], node, values)
                    if result is not None:
                        return result

        path = url.split('/')
        result = walk(path[1:], self._root, {})
        if result is None:
            raise LookupError("URL not found", url)
        return result

    def replace_controller(self, old_controller, new_controller):
        def walk(node):
            if node.ctrl is old_controller:
                node.ctrl = new_controller
            else:
                for child in node.children:
                    walk(child)
        walk(self._root)


    def get_controllers(self):
        controllers = []
        def walk(node, params=()):
            if isinstance(node.value, _PathParameter):
                params += (node.value.name, )
            if node.ctrl is not None:
                controllers.append((node.ctrl, params))
            for child in node.children:
                walk(child, params)
        walk(self._root)
        return controllers

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
        if url_prefix != '' and not url_prefix.startswith('/'):
            raise ValueError("url_prefix must start with '/' or be an empty string")
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
            self.get_urls.add(self.url_prefix + url, ctrl)
            for key, value in kwargs.items():
                setattr(ctrl, key, value)
            return ctrl
        return decorator

    def put(self, url):
        """
        Return decorator to link URL with put method to controller
        """
        def decorator(ctrl):
            self.put_urls.add(self.url_prefix + url, ctrl)
            return ctrl
        return decorator

    def post(self, url):
        """
        Return decorator to link URL with post method to controller
        """
        def decorator(ctrl):
            self.post_urls.add(self.url_prefix + url, ctrl)
            return ctrl
        return decorator

    def delete(self, url):
        """
        Return decorator to link URL with delete method to controller
        """
        def decorator(ctrl):
            self.del_urls.add(self.url_prefix + url, ctrl)
            return ctrl
        return decorator

    def crud(self, url, resource):
        """
        Generate controllers for resource.
        url must have word surrounded by square brackets in order to define
        id position in url used by delete, put and get controller.
        """
        if not url.startswith('/'):
            raise ValueError("url must start with '/'")

        # FIXME raise an error if url hasn't brackets.
        resources_url = ''
        single_resource_url = ''
        for word in url.strip('/').split('/'):
            if word.startswith('['):
                substitution = word.replace('[', '{').replace(']', '}')
                single_resource_url += '/' + substitution
            else:
                resources_url += '/' + word
                single_resource_url += '/' + word

        decorator = self.get(single_resource_url)
        decorator(GetSingleControllerBuilder(resource))

        decorator = self.get(resources_url)
        decorator(GetControllerBuilder(resource))

        decorator = self.post(resources_url)
        decorator(PostControllerBuilder(resource))

        decorator = self.put(single_resource_url)
        decorator(PutControllerBuilder(resource))

        decorator = self.delete(single_resource_url)
        decorator(DeleteControllerBuilder(resource))


class GetSingleControllerBuilder:
    """
    Generate controller for get single resource request.
    """
    single = True
    optimizable = False

    def __init__(self, resource):
        self.resource = resource
        self.resource.on_initialized.append(self.on_initialized)

    def on_initialized(self):
        self.optimizable = not self.resource.Meta.composed

    def __call__(self, **kwargs):
        field = self.resource._id_fields_names[0]
        where_clause = getattr(self.resource, field) == kwargs[field]
        for field in self.resource._id_fields_names[1:]:
            where_clause &= getattr(self.resource, field) == kwargs[field]

        try:
            resource = next(iter(self.resource.select().where(where_clause)))
        except StopIteration:
            return None
        else:
            return resource.to_dict()


class GetControllerBuilder:
    """
    Generate controller for get resources request.
    """

    optimizable = False

    def __init__(self, resource):
        self.resource = resource
        self.resource.on_initialized.append(self.on_initialized)

    def on_initialized(self):
        self.optimizable = not self.resource.Meta.composed
        weak_id = [field.name for field in self.resource.Meta.weak_id]
        if weak_id:
            self.inherited_ids = [field_name
                                  for field_name
                                  in self.resource._id_fields_names
                                  if field_name not in weak_id]
        else:
            self.inherited_ids = []

    def __call__(self, **kwargs):
        if self.inherited_ids:
            field = self.inherited_ids[0]
            where_clause = getattr(self.resource, field) == kwargs[field]
            for field in self.inherited_ids[1:]:
                where_clause &= getattr(self.resource, field) == kwargs[field]
            return [resource.to_dict()
                    for resource
                    in self.resource.select().where(where_clause)]

        else:
            return [resource.to_dict()
                    for resource
                    in self.resource.select()]



class PostControllerBuilder:
    """
    Generate controller for post resources request.
    """

    def __init__(self, resource):
        self.resource = resource
        self.resource.on_initialized.append(self.on_initialized)

    def on_initialized(self):
        weak_id = [field.name for field in self.resource.Meta.weak_id]
        if weak_id:
            self.inherited_ids = [field_name
                                  for field_name
                                  in self.resource._id_fields_names
                                  if field_name not in weak_id]
        else:
            self.inherited_ids = []

    def __call__(self, body, **kwargs):
        for name in self.inherited_ids:
            body[name] = kwargs[name]
        return self._save(body).to_dict()

    def _save(self, body):
        instance = self.resource(**body)
        instance.save()
        return instance


class PutControllerBuilder:
    """
    Generate controller for put resources request.
    """

    def __init__(self, resource):
        self.resource = resource
        self.resource.on_initialized.append(self.on_initialized)

    def on_initialized(self):
        weak_id = [field.name for field in self.resource.Meta.weak_id]
        self.inherited_ids = [field_name
                              for field_name
                              in self.resource._id_fields_names
                              if field_name not in weak_id]

    def __call__(self, body, **kwargs):
        for field_name in self.inherited_ids:
            body[field_name] = kwargs[field_name]

        instance = self.resource(**body)
        instance.update()
        return instance.to_dict()


class DeleteControllerBuilder:
    """
    Generate controller for delete resources request.
    """

    def __init__(self, resource):
        self.resource = resource

    def __call__(self, **kwargs):
        field = self.resource._id_fields_names[0]
        where_clause = getattr(self.resource, field) == kwargs[field]
        for field in self.resource._id_fields_names[1:]:
            where_clause &= getattr(self.resource, field) == kwargs[field]

        instance = list(self.resource.select().where(where_clause))[0]
        instance.delete()
