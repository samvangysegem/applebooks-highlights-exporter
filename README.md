# BookBits - Apple Books Highlight Exporter

A simple (*forked*) command-line tool to export highlights and notes from Apple Books on macOS.

## Example MD output

'''
# Breakneck
*Dan Wang*

## a08_Chapter01

> an enthusiasm to become engineers of the soul
2021-12-03 11:24 AM EST

> Engineers often treat social issues as math exercises.
2021-12-03 11:40 AM EST

> Alexis de Tocqueville, “is not composed of the rich . . . but occupies the judicial bench and the bar.”
2021-12-04 09:57 AM EST

## a09_Chapter02

> Chongqing is my favorite Chinese city to visit because it has the country’s, and perhaps the world’s, most dramatic urban setti
ng. Highways and bridges weave through huge buildings that look as if they are carved into the hills, connected to each other by
systems of stairs, escalators, and walkways. The city is filled with ludicrous designs, like a subway line that passes through th
e middle of an apartment building sitting on a hill.
2021-12-15 11:00 PM EST

> In 2010, only half of Guizhou’s children attended high school—the lowest rate in the country.
2021-12-15 11:09 PM EST
'''

## Features

- Exports highlights and notes from Apple Books
- Supports both CSV and Markdown export formats
- User-friendly terminal interface for book and format selection
- Works with the local Apple Books library on macOS
- Groups highlights in chapter sections (extracted as is)
- Includes date annotations with each highlight
- Includes Title and Author in export

(Only tested on highlights exporting to MD)

## Requirements

- macOS with Apple Books
- Python 3.6+
- `simple_term_menu` library

## Usage

1. Clone the repository
2. Install the required library: `pip install simple_term_menu`
3. Run the script: `python apple_books_exporter.py`
4. Follow the on-screen prompts to select a book and export format
5. Find your exported highlights in the same directory as the script

## Note

This is a work in progress.

