from copy import copy
from warnings import warn


class SchemaGenerator(object):
    """
    base schema generator. This contains the common interface for
    all subclasses:

    * match_schema
    * match_object
    * init
    * add_schema
    * add_object
    * to_schema
    """
    KEYWORDS = ('type','min','max','format','enum','example','unique', 'default')

    @classmethod
    def match_schema(cls, schema):
        raise NotImplementedError("'match_schema' not implemented")

    @classmethod
    def match_object(cls, obj):
        raise NotImplementedError("'match_object' not implemented")

    def __init__(self, node_class):
        self.node_class = node_class
        self.MIN = None
        self.MAX = None
        self.FORMAT = None
        self.EXAMPLE = None
        self.UNIQUE = None
        self.ENUM = set()
        self.SCHEMA_ERROR = []
        self._extra_keywords = {}
        self.init()

    def init(self):
        pass

    def add_schema(self, schema):
        self.add_extra_keywords(schema)

    def add_extra_keywords(self, schema):
        for keyword, value in schema.items():
            if keyword in self.KEYWORDS:
                if keyword == "max":
                    self.MAX = value
                if keyword == "min":
                    self.MIN = value
                if keyword == "format":
                    self.FORMAT = value
                if keyword == "example":
                    self.EXAMPLE = value
                if keyword == "unique":
                    self.UNIQUE = value
                if keyword == "enum":
                    self.ENUM = value
                continue
            elif keyword not in self._extra_keywords:
                self._extra_keywords[keyword] = value
            elif self._extra_keywords[keyword] != value:
                warn(('Schema incompatible. Keyword {0!r} has conflicting '
                      'values ({1!r} vs. {2!r}). Using {1!r}').format(
                          keyword, self._extra_keywords[keyword], value))

    def add_object(self, obj, parent, mode="learn"):
        pass

    def to_schema(self):
        return copy(self._extra_keywords)


class TypedSchemaGenerator(SchemaGenerator):
    """
    base schema generator class for scalar types. Subclasses define
    these two class constants:

    * `JS_TYPE`: a valid value of the `type` keyword
    * `PYTHON_TYPE`: Python type objects - can be a tuple of types
    """

    @classmethod
    def match_schema(cls, schema):
        return schema.get('type') == cls.JS_TYPE

    @classmethod
    def match_object(cls, obj):
        return isinstance(obj, cls.PYTHON_TYPE)

    def to_schema(self):
        schema = super(TypedSchemaGenerator, self).to_schema()
        schema['type'] = self.JS_TYPE
        schema['min'] = self.MIN
        schema['max'] = self.MAX
        schema['format'] = self.FORMAT
        schema['example'] = self.EXAMPLE
        if self.UNIQUE:
            schema['unique'] = self.UNIQUE
        if len(self.ENUM):
            schema['enum'] = list(self.ENUM)
        if len(self.SCHEMA_ERROR):
            schema['schema_error'] = self.SCHEMA_ERROR
        return schema
