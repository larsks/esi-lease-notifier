import jinja2

from pathlib import Path
from prettytable import PrettyTable


def filter_tabulate(
    data: list[list[str]], headings: list[str] | None = None, html: bool = False
) -> str:
    table = PrettyTable()
    if headings:
        table.field_names = headings

    table.add_rows(data)

    if html:
        return table.get_html_string()
    else:
        return table.get_string()


def create_template_environment(template_path: str | Path) -> jinja2.Environment:
    env = jinja2.Environment(loader=jinja2.loaders.FileSystemLoader(str(template_path)))
    env.filters["tabulate"] = filter_tabulate
    return env
