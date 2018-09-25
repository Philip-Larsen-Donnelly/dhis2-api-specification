from .base import SchemaGenerator, TypedSchemaGenerator
import re


class Typeless(SchemaGenerator):
    """
    schema generator for schemas with no type. This is only used when
    there is no other active generator, and it will be merged into the
    first typed generator that gets added.
    """

    @classmethod
    def match_schema(cls, schema):
        return 'type' not in schema

    @classmethod
    def match_object(cls, obj):
        return False


class Null(TypedSchemaGenerator):
    """
    generator for null schemas
    """
    JS_TYPE = 'null'
    PYTHON_TYPE = type(None)


class Boolean(TypedSchemaGenerator):
    """
    generator for boolean schemas
    """
    JS_TYPE = 'boolean'
    PYTHON_TYPE = bool


class String(TypedSchemaGenerator):
    """
    generator for string schemas - works for ascii and unicode strings
    """
    JS_TYPE = 'string'
    PYTHON_TYPE = (str, type(u''))

    def get_format(self,obj):
        """
        work out the most likely format
        """
        #
        if re.match(r"htt", obj):
            format = "url"

        elif re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", obj):
            format = "email"

        elif re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z*", obj):
            format = "date-time"

        elif re.match(r"^[0-9a-zA-Z]{11}$", obj):
            format = "uid"
            if re.match(r"^[A-Z_]+$", obj):
                format = "enum"
            if re.match(r"^[A-Z][a-z]{10}$", obj):
                format = "general"

        elif re.match(r"^#[0-9a-fA-F]{6}$", obj):
            format = "COLOR"

        elif re.match(r"^[A-Z_]+$", obj):
            format = "enum"
            # enum cannot be true for unique attributes
            if self.UNIQUE:
                format = "general"

        elif re.match(r"^[-rw]+$", obj):
            format = "access"

        else:
            format = "general"

        return format

    def add_object(self, obj, parent, mode):
        if self.MIN is None or len(obj) < self.MIN:
            if mode != "learn":
                # testing mode
                self.SCHEMA_ERROR += ['value smaller than schema minimum']
            self.MIN = len(obj)
        if self.MAX is None or len(obj) > self.MAX:
            if mode != "learn":
                # testing mode
                self.SCHEMA_ERROR += ['value larger than schema maximum']
            self.MAX = len(obj)
        newFormat = self.get_format(obj)
        if self.FORMAT == "enum":
            self.ENUM.add(obj)
        else:
            self.ENUM.clear()
        if self.FORMAT is None or newFormat != self.FORMAT:
            if self.FORMAT is not None:
                print("SCHEMA-FORMAT_CHANGE - Attribute:",parent,"Value:",obj,"From:",self.FORMAT,"To:",newFormat)
            if mode != "learn" and newFormat != None:
                # testing mode
                self.SCHEMA_ERROR += ['value format '+newFormat+' does not match schema format '+ self.FORMAT]
            self.FORMAT = newFormat
        if self.EXAMPLE is None:
            self.EXAMPLE = obj
        


class Number(SchemaGenerator):
    """
    generator for integer and number schemas. It automatically
    converts from `integer` to `number` when a float object or a
    number schema is added
    """
    JS_TYPES = ('integer', 'number')
    PYTHON_TYPES = (int, float)

    @classmethod
    def match_schema(cls, schema):
        return schema.get('type') in cls.JS_TYPES

    @classmethod
    def match_object(cls, obj):
        return type(obj) in cls.PYTHON_TYPES

    def init(self):
        self._type = 'integer'
        #print("INIT number") #PPPP

    def add_schema(self, schema):
        #print("AddSchemaObject--",obj) #PPPP
        self.add_extra_keywords(schema)
        if schema.get('type') == 'number':
            self._type = 'number'

    def add_object(self, obj, parent, mode):
        #print("AddNumberObject--",obj) #PPPP
        if self.MIN is None or obj < self.MIN:   
            if mode != "learn":
                # testing mode         
                print(obj ,"smaller than schema min", self.MIN)
            self.MIN = obj
        if self.MAX is None or obj > self.MAX:
            if mode != "learn":
                # testing mode
                print(obj, "larger than schema max", self.MAX)
            self.MAX = obj
        if isinstance(obj, float):
            self._type = 'number'
        if self.EXAMPLE is None:
            self.EXAMPLE = obj


    def to_schema(self):
        schema = super(Number, self).to_schema()
        schema['type'] = self._type
        schema['min'] = self.MIN
        schema['max'] = self.MAX
        schema['format'] = self.FORMAT
        schema['example'] = self.EXAMPLE
        if len(self.ENUM):
            schema['enum'] = self.ENUM
        if len(self.SCHEMA_ERROR):
            schema['schema_error'] = self.SCHEMA_ERROR
        #print("NumberToSchema---",self.MIN) #PPPP
        return schema