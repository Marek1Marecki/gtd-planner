# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import django

# Wskazujemy folder 'web' jako root kodu
sys.path.insert(0, os.path.abspath('../../web'))

# Inicjalizacja Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'gtd_calendar.settings'
# Podajemy atrapy dla Mypy/Sphinx (tak jak w Makefile)
os.environ['DATABASE_URL'] = 'postgres://u:p@localhost:5432/db'
os.environ['SECRET_KEY'] = 'docs-key'
django.setup()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'GTD_Planner'
copyright = '2026, Dominik'
author = 'Dominik'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',      # Wyciąga docs z kodu
    'sphinx.ext.napoleon',     # Obsługuje Google Style (to co dopisał Windsurf)
    'sphinx.ext.viewcode',     # Dodaje linki do kodu źródłowego
    'sphinx_autodoc_typehints',# Ładnie renderuje typy z MyPy
]

templates_path = ['_templates']
exclude_patterns = []

language = 'pl'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
