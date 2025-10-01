import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "Guage-Kit"
copyright = "2025, Neo Pragnya"
author = "Neo Pragnya"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints"
]
html_theme = "sphinx_rtd_theme"  # Using RTD theme instead of Wagtail for now
html_theme_options = {
    "show_toc_sidebar": True
}
html_sidebars = {
    "**": ["globaltoc.html", "localtoc.html", "searchbox.html"]
}

# Support for markdown files
source_suffix = {
    '.rst': None,
    '.md': None,
}