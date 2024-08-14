# Shotmaker

## Overview

Shotmaker is a flexible Python library designed to simplify generating and validating few-shot
prompts for Large Language Models (LLMs). It provides a powerful templating system that allows
users to easily format examples and queries, and parse LLM responses, supporting various data formats.

## Features

- Template-based prompt generation with support for examples and queries
- Flexible formatting of prompt components using interchangeable DataConverters
- Support for various data formats (String, Markdown tables, XML, JSON)
- Jinja2-based templating for overall prompt structure
- Automatic validation of template variables against provided context
- Easy parsing of LLM responses based on the same template structure

## Installation

```bash
pip install git+https://github.com/Permafacture/shotmaker.git  # Note: Not yet published to PyPI
```

## Quick Start

```python
from shotmaker import PromptEngine, PromptComponentFormatter, StringConverter, LineTemplateConverter

# Initialize formatters
component_formatter = PromptComponentFormatter({
    'passage': StringConverter(),
    'summary': StringConverter(),
    'entities': LineTemplateConverter('name (type)', fields=['name', 'type'], indent=4)
})

# Create PromptEngine
prompt_engine = PromptEngine(component_formatter)  # default prompt template used

# Prepare context, examples, and query
context = {
    'system_prompt': 'You are a helpful AI assistant.',
    'task_description': 'Summarize the passage and extract entities.'
}

examples = [
    {'passage': 'Example passage 1', 'summary': 'Example summary 1', 'entities': [{'name': 'Entity1', 'type': 'Type1'}]},
    {'passage': 'Example passage 2', 'summary': 'Example summary 2', 'entities': [{'name': 'Entity2', 'type': 'Type2'}]}
]

query = {'passage': 'Query passage'}

# see a single formatted example
print(component_formatter.format_example(examples[0]))

# Passage:
# Example passage 1
# 
# Summary:
# Example summary 1
# 
# Entities:
#     Entity1 (Type1)

# Generate prompt
prompt = prompt_engine.generate_prompt(context, examples, query)

# Use prompt with your LLM API
response = llm_api.generate(prompt)

# Parse LLM response
result = prompt_engine.parse_result(response)

# Serialize and deserialize prompt engine
json_string = sm.serialization.to_json(prompt_engine)
new_prompt_engine = sm.serialization.from_json(json_string)
result_from_reconstructed = new_prompt_engine.parse_result(reponse)

# Load few shot examples from text file in same format as prompt
# It doesn;t make sense to just load the prompt, but examples and
#   the prompt are in the same format so this shows the loading ability

reconstructed_examples = prompt_engine.load(prompt)
examples == reconstructed_examples[:2]  # last item is the query
```

## Support

If you encounter any issues or have questions, please file an issue on the GitHub issue tracker.

## Future Work

Future work will focus on adding functionality to facilitate validating and evaluating prompts
with an sklearn inspired api

    - Utilities for doing sweeps over paramters
    - Evaluating LLM responses against known truth or against an LLM judge
    - Bayesian exploration or parameter space combined with evaluation to arrive at the best
          model, prompt, shot selection and shot formatting combination


Shotmaker is named after the early 90's post-hardcore band of the same name: https://shotmaker.bandcamp.com/album/a-moment-in-time-1993-1996
