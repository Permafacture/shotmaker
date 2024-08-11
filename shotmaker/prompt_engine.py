from abc import ABC, abstractmethod
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, meta
from shotmaker.data_converters import DataConverter, StringConverter

def format_key(key: str) -> str:
    # TODO make this more customizeable
    return f"{key.title()}:\n"

class PromptComponentFormatter:
    def __init__(self, converters: Dict[str, DataConverter]):
        self.converters = converters

    def format_example(self, example: Dict[str, Any]) -> str:
        return self._format_dict(example)

    def format_query(self, query: Dict[str, Any]) -> str:
        return self._format_dict(query)

    def _format_dict(self, data: Dict[str, Any]) -> str:
        formatted_parts = []
        for key, value in data.items():
            converter = self.converters.get(key, StringConverter())
            formatted_value = converter.format(value)
            formatted_parts.append(f"{format_key(key)}{formatted_value}")
        return "\n\n".join(formatted_parts)

    def parse_result(self, result: str) -> Dict[str, Any]:
        parsed_parts = {}
        for key, converter in self.converters.items():
            start_index = result.find(format_key(key))
            if start_index == -1:
                parsed_parts[key] = None
                continue
            end_index = result.find("\n\n", start_index)
            if end_index == -1:
                end_index = len(result)
            formatted_part = result[start_index + len(format_key(key)):end_index].strip()
            parsed_parts[key] = converter.parse(formatted_part)
        return parsed_parts


class PromptEngine:
    def __init__(self, template_file: str, component_formatter: PromptComponentFormatter):
        self.env = Environment(loader=FileSystemLoader('.'))
        self.template = self.env.get_template(template_file)
        self.component_formatter = component_formatter
        self.required_variables = self._get_required_variables()

    def _get_required_variables(self) -> set:
        source = self.env.loader.get_source(self.env, self.template.filename)
        ast = self.env.parse(source)
        return meta.find_undeclared_variables(ast)

    def _validate_context(self, context: Dict[str, Any], examples: List[Dict[str, Any]], query: Dict[str, Any]):
        provided_vars = set(context.keys()) | {'examples', 'query'}
        missing_vars = self.required_variables - provided_vars
        if missing_vars:
            raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")

    def generate_prompt(self, context: Dict[str, Any], examples: List[Dict[str, Any]], query: Dict[str, Any]) -> str:
        self._validate_context(context, examples, query)

        formatted_examples = [self.component_formatter.format_example(ex) for ex in examples]
        formatted_query = self.component_formatter.format_query(query)

        full_context = {
            **context,
            'examples': formatted_examples,
            'query': formatted_query
        }

        return self.template.render(full_context)

    def parse_result(self, result: str) -> Dict[str, Any]:
        return self.component_formatter.parse_result(result)
