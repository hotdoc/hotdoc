class GtkDocCommentBlock(object):
    def __init__(self, name, annotations, params, description, tags):
        self.params = {}
        for param in params:
            self.params[param.name] = param
        self.name = name
        self.retval_block = None
        self.description = description
        self.annotations = annotations
        self.tags = {}
        for tag in tags:
            self.tags[tag.name] = tag

    def add_param_block (self, param_name, block):
        self.params[param_name] = block

    def set_return_block (self, block):
        self.tags['returns'] = block

    def set_description (self, description):
        self.description = description.strip();

class GtkDocAnnotation(object):
    def __init__ (self, name, argument):
        self.name = name
        self.argument = argument

class GtkDocTag(object):
    def __init__(self, name, value, annotations, description):
        self.name = name
        self.value = value
        self.annotations = annotations
        self.description = description

class GtkDocParameter(object):
    def __init__(self, name, annotations, description):
        self.name = name
        self.annotations = annotations
        self.description = description
