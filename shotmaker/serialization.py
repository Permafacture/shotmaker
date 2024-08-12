import json
import inspect
import importlib
from typing import Any, Dict, Type

# Use these function to serializae and deserialize

def to_json(obj):
    """Create a JSON string from a Jsonizeable object"""
    return json.dumps(obj.to_json())

def from_json(json_string):
    """Deserialize a JSON string into a Jsonizeable object"""
    json_data = json.loads(json_string)
    return Jsonizeable.from_json(json_data)

class Jsonizeable:
    """
    A mixin class that provides JSON serialization and deserialization capabilities.

    This is intended to save and load the configuation of simple objects and not
    Pickle which saves the states of objects

    This class implements two main methods:
    - to_json(): Serializes the object to a JSON-compatible dictionary.
    - from_json(): Deserializes a JSON-compatible dictionary back into an object.

    Classes that inherit from Jsonizeable should follow these guidelines:
    1. Ensure that all parameters in the __init__ method correspond to object attributes
           with the same names. Transformations of the input values should be stored on
           separate attributes
    2. Use only JSON-serializable types (str, int, float, bool, None) or Jsonizeable
           objects as attribute values, as well as lists and dicts containing
           those types.
    3. Serialized objects are instantiated when they are encountered and each is a unique
           instance. Objects sharing a reference to a single object will have seperate
           objects after deserialization
    4. All classes must be defined in this same module as Jsonizeable. Have not tested
           having Jsonizeable be defined in it's own module

    """

    @classmethod
    def from_json(cls, json_data):
        class_name = json_data.pop('__class__')
        module_name = json_data.pop('__module__')
        
        # Import the module and get the class
        module = importlib.import_module(module_name)
        class_type = getattr(module, class_name)
        
        # Recursively deserialize nested Jsonizeable objects, lists, and dicts
        for key, value in json_data.items():
            json_data[key] = cls._deserialize_value(value)
        
        # Create and return the instance
        return class_type(**json_data)

    @classmethod
    def _deserialize_value(cls, value):
        if isinstance(value, dict):
            if '__class__' in value:
                return cls.from_json(value)
            return {k: cls._deserialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls._deserialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: cls.from_json(v) if (isinstance(v, dict) and '__class__' in v) else v
                       for k, v in value.items()
                       }
        return value

    def to_json(self):
        result = {
            '__class__': self.__class__.__name__,
            '__module__': self.__class__.__module__
        }
        
        # Get the signature of the __init__ method
        signature = inspect.signature(self.__init__)
        
        for param_name in signature.parameters:
            if param_name == 'self':
                continue
            
            value = getattr(self, param_name)
            
            if isinstance(value, Jsonizeable):
                result[param_name] = value.to_json()
            elif isinstance(value, (str, int, float, bool, type(None))):
                result[param_name] = value
            elif isinstance(value, (list, tuple)):
                result[param_name] = [
                    item.to_json() if isinstance(item, Jsonizeable) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                result[param_name] = {
                    k: v.to_json() if isinstance(v, Jsonizeable) else v
                    for k, v in value.items()
                }
            else:
                raise ValueError(f"Unsupported type for attribute {param_name}: {type(value)}")
        
        return result
