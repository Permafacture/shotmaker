import re
import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, meta
from shotmaker.data_converters import DataConverter, StringConverter, BasicDelimiter
from shotmaker.serialization import Jsonizeable

def format_key(key: str) -> str:
    # TODO make this more customizeable
    return f"{key.title()}:"

default_template = Path(__file__).parent / 'default_prompt.txt'

class PromptComponentFormatter(Jsonizeable):

    def __init__(self, converters):
        """
        :param converters: Dictionary mapping keys to DataConverter instances
        """
        # Capture input for Jsonizeable
        self.converters = converters

    def format_example(self, example):
        """
        Format an dictionary of data representing a shot into a string for the prompt.
        
        :param example: Dictionary containing example data
        :return: Formatted shot string
        """
        return self._format_dict(example)

    def format_query(self, query):
        """
        A query is an incomplete example which the LLM will complete to give us a result.
        The formatted string will include the first key for which we don;t provide a value
        to prompt the LLM to start there. 
        
        :param query: Dictionary containing an incomplete example
        :return: Formatted query string with the next expected key
        """
        last_supplied_key = list(query.keys())[-1]
        keys = list(self.converters.keys())
        next_key = keys[keys.index(last_supplied_key) + 1]
        return self._format_dict(query) + f"\n\n{format_key(next_key)}"

    def _format_dict(self, data):
        """
        General dictionary to string for prompt used for both examples and the query
        
        :param data: Dictionary to format
        :return: Formatted string representation of the dictionary
        """
        formatted_parts = []
        for key, value in data.items():
            converter = self.converters.get(key)
            if converter is None:
                continue
            formatted_value = converter.format(value)
            formatted_parts.append(f"{format_key(key)}{formatted_value}")
        return "\n\n".join(formatted_parts)

    def parse_result(self, result):
        """
        Parse a formatted string result back into a dictionary.
        
        :param result: Formatted string to parse
        :return: Dictionary of parsed values
        """
        parsed_parts = {}
        keys = list(self.converters.keys())
        result = result.strip()

        parts = []
        for i, key in enumerate(keys):
            match = re.search(f"(^|\n){re.escape(format_key(key))}", result)
            if not match:
                parsed_parts[key] = None
                continue

            start, end = match.span()
            parts.append((start, end, key))

        parts.sort()

        # if this was a completion, the result may begin with completing the section that came before this
        first_key = parts[0][2]
        if keys.index(first_key) != 0 and parts[0][0] != 0:
            parts = [(0, 0, keys[keys.index(first_key)-1])] + parts

        for start, stop in zip(parts, parts[1:]):
            key = start[2]
            formatted_part = result[start[1]:stop[0]].strip()
            if not formatted_part:
                parsed_parts[key] = None
            else:
                parsed_parts[key] = self.converters[key].parse(formatted_part)

        stop = parts[-1]
        key = stop[2]
        formatted_part = result[stop[1]:].strip()
        parsed_parts[key] = self.converters[key].parse(formatted_part) if formatted_part else None

        return parsed_parts


class PromptEngine(Jsonizeable):
    def __init__(self, component_formatter, delimiter=None, template_file=default_template):
        """
        Generates prompt from template utilizing the component formatter to format the
        shots and query 

        :param component_formatter: PromptComponentFormatter instance
        :param delimiter_obj: (optional) Delimiter instance. If not provided than a sensible
            default is used
        :param template_file: (optional) file containing Jinja2 template. default template used
            if not provided
        """
        # capture input params for Jsonizeable
        self.component_formatter = component_formatter
        self.delimiter = delimiter
        self.template_file = str(template_file)

        # Do rest of instantiation
        self.delimiter_obj = delimiter or BasicDelimiter('=', 6)
        template_file = Path(template_file).resolve()
        self.env = Environment(loader=FileSystemLoader(str(template_file.parent)))
        self.template = self.env.get_template(template_file.parts[-1])
        self.required_variables = self._get_required_variables()

    def _get_required_variables(self):
        source = self.env.loader.get_source(self.env, self.template.name)
        ast = self.env.parse(source)
        return meta.find_undeclared_variables(ast)

    def _validate_context(self, context, examples, query):
        """ Validate that all required variables are supplied to the template """
        provided_vars = set(context.keys()) | {'examples', 'query'}
        missing_vars = self.required_variables - provided_vars
        if missing_vars:
            raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")

    def generate_prompt(self, context, examples, query):
        """
        Compose the few shot prompt ready to go to LLM. Result can be parsed to retrieve the
        completion of the query in the same format as the example dictionaries.

        "param context: Dict of strings where keys are varibale names in the jinja 2 template
        "param examples: List of dicts of strings with keys matching the keys of the component formatter
        :param query: Dict of strings with missing values to be completed by the LLM
        :return: prompt ready to go to LLM
        """
        context = {'delimiter': self.delimiter_obj.format(), **context}
        self._validate_context(context, examples, query)

        formatted_examples = [self.component_formatter.format_example(ex) for ex in examples]
        formatted_query = self.component_formatter.format_query(query)

        full_context = {
            **context,
            'examples': formatted_examples,
            'query': formatted_query
        }

        return self.template.render(full_context)

    def parse_result(self, result):
        """ Parse the response from the LLM

        :param result: string from the LLM
        :return: Dictionary representing a completed example
        """
        return self.component_formatter.parse_result(result)

    def load(self, serialized_examples):
        """
        Load and parse multiple examples from a serialized string.
        
        :param serialized_examples: String containing multiple serialized examples
        :return: List of parsed example dictionaries
        """
        return [self.parse_result(E) for E in self.delimiter_obj.split(serialized_examples)]
