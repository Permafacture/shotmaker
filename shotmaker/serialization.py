import json
import inspect
import importlib
from typing import Any, Dict, Type

def to_json(obj):
    return json.dumps(obj.to_json())

def from_json(json_string):
    json_data = json.loads(json_string)
    return Jsonizeable.from_json(json_data)

class Jsonizeable:

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
