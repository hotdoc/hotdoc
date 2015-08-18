class CommentBlock(object):
    def __init__ (self):
        self.params = {}
        self.description = None
        self.tags = {}

    def add_param_block (self, param_name, block):
        self.params[param_name] = block

    def set_return_block (self, block):
        self.tags['returns'] = block

    def set_description (self, description):
        self.description = description.strip();

class GtkDocCommentBlock(CommentBlock):
    def __init__(self, name, filename, lineno, annotations, params, description, tags):
        CommentBlock.__init__(self)
        self.short_description = None
        self.title = None
        self.filename = filename
        self.lineno = lineno

        for param in params:
            if param.name.lower() == 'short_description':
                self.short_description = param.description
            elif param.name.lower() == 'title':
                self.title = param.description
            else:
                self.params[param.name] = param
        self.name = name
        self.description = description
        self.annotations = {}
        for annotation in annotations:
            self.annotations[annotation.name] = annotation
        for tag in tags:
            self.tags[tag.name.lower()] = tag

class GtkDocAnnotation(object):
    def __init__ (self, name, argument):
        self.name = name
        self.argument = argument

class GtkDocTag(object):
    def __init__(self, name, value, annotations, description):
        self.name = name
        self.value = value
        self.annotations = {}
        for annotation in annotations:
            self.annotations[annotation.name] = annotation
        self.description = description

class GtkDocParameter(object):
    def __init__(self, name, annotations, description):
        self.name = name
        self.annotations = {}
        for annotation in annotations:
            self.annotations[annotation.name] = annotation
        self.description = description
