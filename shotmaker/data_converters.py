import re
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from shotmaker.serialization import Jsonizeable

class Delimiter(ABC, Jsonizeable):

    def __init__(self):
        # ABC's must be givin an init for Jsonizeable
        pass

    @abstractmethod
    def format(self):
        """return string to delimit examples by"""
        pass

    @abstractmethod
    def split(self, formatted_text):
        """split formatted text by example delimiter and return list"""
        pass

class BasicDelimiter(Delimiter):
    """Simple delimiter that just puts a line that consists of a character repeated"""

    def __init__(self, char, n=5):
        self.char = char
        self.n = n
        self._setup()
  
    def _setup(self):
        self._regex = re.compile(f"\n{self.char}{{{self.n},}}\n")

    def format(self):
        return f"\n{self.char*self.n}\n"

    def split(self, formatted_text):
        return self._regex.split(formatted_text)

class DataConverter(ABC, Jsonizeable):
    def __init__(self):
        # ABC's must be givin an init for Jsonizeable
        pass

    @abstractmethod
    def format(self, data: Any) -> str:
        pass

    @abstractmethod
    def parse(self, formatted_str: str) -> Any:
        pass


class StringConverter(DataConverter):
    def format(self, data: Any) -> str:
        return str(data)

    def parse(self, formatted_str: str) -> Any:
        return formatted_str.strip()

class LineTemplateConverter(DataConverter):
    ''' Format a List of Dicts into a template string
    fields are delimited by template_characters, which are characters that
    can only be in the template. Template characters appearing in a value will
    break the parsing.

    example templates:
        "key1 key2"          not valid because keys are not seperated by template characters
        "key1 | key2"        valid
        "key1 | AAA | key2"  valid
        "key1 AAA key2"      will validate but won't work

    stick to spaces and template characters in your template for best results

    # TODO make "key1 AAA key2" fail validation
    # TODO should template characters be automatically determined? Or is explicit better?

    >>> data = [{'key1': 'Bob', 'key2': 'Person'},
    >>>         {'key1': 'Alice', 'key2': 'Person'},
    >>>         {'key1': 'Rover', 'key2': 'Dog'}]
    >>>
    >>> formatter = LineTemplateConverter("key1 (key2)", fields=['key1', 'key2'])
    >>> formatted = formatter.format(data)
    >>> print(formatted)
    >>> parsed = formatter.parse(formatted)
    >>> parsed == data

    outputs:
        Bob (Person)
        Alice (Person)
        Rover (Dog)
    '''

    def __init__(self, template, fields, template_characters='(){}[]|;:'):
        self.template = template
        self.fields = fields
        self.template_characters = template_characters
        self._validate_template()
        self.pattern = self._create_pattern()

    def _validate_template(self):
        value_pattern = f"[^{re.escape(self.template_characters+' ')}]+"
        pieces = value_pattern.split(self.template)
        assert all(len(delim) > 0 for delim in pieces[1:-1])

    def _create_pattern(self):
        template_characters = self.template_characters
        value_pattern = f"[^{re.escape(template_characters)}]+"

        # validate template and remove spaces
        template = self.template
        split = re.split('|'.join(self.fields), template)
        assert not any(set(p) in (set(), set(' ')) for p in split[1: -1])  # keys are separated
        for field in self.fields:
            template = field.join(x.strip() for x in re.split(field, template))

        pattern = re.escape(template)
        for field in self.fields:
            pattern = pattern.replace(field, f"(?P<{field}>{value_pattern})")

        return re.compile(f"^{pattern}$")

    def _format_line(self, data):
        missing_keys = set(self.fields) - set(data.keys())
        if missing_keys:
            raise ValueError(f"Missing keys in data: {missing_keys}")

        result = self.template
        for field in self.fields:
            result = result.replace(field, data[field].strip())
        return result

    def _parse_line(self, string):
        match = self.pattern.match(string)
        if not match:
            raise ValueError("Input string does not match the template format")

        return {field: match.group(field).strip() for field in self.fields}

    def format(self, data):
        return '\n'.join(self._format_line(item) for item in data)

    def parse(self, string):
        return [self._parse_line(line.strip()) for line in string.split('\n')]


class MarkdownTableConverter(DataConverter):
    def format(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""

        headers = list(data[0].keys())
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "|" + "|".join(["-------" for _ in headers]) + "|"
        data_rows = []
        for item in data:
            row = "| " + " | ".join(str(item.get(header, "")) for header in headers) + " |"
            data_rows.append(row)

        markdown_table = "\n".join([header_row, separator_row] + data_rows)
        return markdown_table

    def parse(self, formatted_str: str) -> List[Dict[str, Any]]:
        lines = formatted_str.strip().split("\n")
        if len(lines) < 3:  # We need at least header, separator, and one data row
            return []

        headers = [h.strip() for h in lines[0].strip("|").split("|")]
        data = []
        for line in lines[2:]:  # Skip header and separator rows
            values = [v.strip() for v in line.strip("|").split("|")]
            data.append(dict(zip(headers, values)))

        return data


class XmlConverter(DataConverter):
    def format(self, data: List[Dict[str, Any]]) -> str:
        root = ET.Element("root")
        for item in data:
            element = ET.SubElement(root, "item")
            for key, value in item.items():
                ET.SubElement(element, key).text = str(value)
        return ET.tostring(root, encoding="unicode", method="xml")

    def parse(self, formatted_str: str) -> List[Dict[str, Any]]:
        root = ET.fromstring(formatted_str)
        result = []
        for item in root.findall("item"):
            item_dict = {}
            for child in item:
                item_dict[child.tag] = child.text
            result.append(item_dict)
        return result


class JsonConverter(DataConverter):
    def format(self, data: List[Dict[str, Any]]) -> str:
        return json.dumps(data, indent=2)

    def parse(self, formatted_str: str) -> List[Dict[str, Any]]:
        return json.loads(formatted_str)
