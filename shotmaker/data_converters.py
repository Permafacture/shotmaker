from abc import ABC, abstractmethod
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
import json

class DataConverter(ABC):
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
