import os
import re
import csv
import glob
import sqlite3
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple

CORE_DATA_EPOCH_OFFSET = 978307200  # seconds between Unix epoch and Core Data epoch (2001-01-01)
EASTERN = ZoneInfo("America/New_York")


def format_timestamp(core_data_ts: float) -> str:
    return datetime.fromtimestamp(core_data_ts + CORE_DATA_EPOCH_OFFSET, tz=EASTERN).strftime("%Y-%m-%d %I:%M %p %Z")
from simple_term_menu import TerminalMenu

# Constants
ANNOTATION_DB_PATTERN = "~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation*.sqlite"
LIBRARY_DB_PATTERN = "~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary*.sqlite"
SUPPORTED_FORMATS = ['csv', 'md']

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_path(pattern: str) -> str:
    """
    Returns the path to a database based on the given pattern.

    Args:
        pattern (str): The glob pattern to search for the database.

    Returns:
        str: The full path to the database.

    Raises:
        FileNotFoundError: If no matching database is found.
    """
    paths = glob.glob(os.path.expanduser(pattern))
    if not paths:
        raise FileNotFoundError(f"No database found matching pattern: {pattern}")
    return paths[0]

def get_library_books() -> Dict[str, Tuple[str, str]]:
    """
    Retrieves all books from the local Apple Books library.

    Returns:
        Dict[str, Tuple[str, str]]: A dictionary where keys are asset IDs and values are tuples
                                    containing the book title and author.

    Raises:
        sqlite3.Error: If there's an issue with the database connection or query.
    """
    try:
        with sqlite3.connect(get_db_path(LIBRARY_DB_PATTERN)) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT ZASSETID, ZSORTTITLE, ZSORTAUTHOR
                              FROM ZBKLIBRARYASSET''')
            return {row[0]: (row[1] or "Unknown Title", row[2] or "Unknown Author") for row in cursor.fetchall()}
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise

def get_library_books_with_highlights() -> List[str]:
    """
    Retrieves asset IDs of books in the local Apple Books library that have 
    highlights or annotations.

    Returns:
        List[str]: A list of asset IDs for books that have highlights or annotations.

    Raises:
        sqlite3.Error: If there's an issue with the database connection or query.
    """
    book_ids = list(get_library_books().keys())
    placeholders = ','.join('?' for _ in book_ids)
    try:
        with sqlite3.connect(get_db_path(ANNOTATION_DB_PATTERN)) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''SELECT DISTINCT ZANNOTATIONASSETID 
                              FROM ZAEANNOTATION 
                              WHERE ZANNOTATIONASSETID IN ({placeholders}) 
                              AND ZANNOTATIONSELECTEDTEXT != "";''', book_ids)
            return [entry[0] for entry in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise

def parse_chapter_from_cfi(cfi: str) -> str:
    match = re.search(r'/6/\d+\[([^\]]+)\]', cfi or '')
    return match.group(1) if match else ""

def cfi_sort_key(cfi: str) -> tuple:
    # CFIs contain numeric path components; lexicographic sort breaks on e.g. /6/10 vs /6/2
    return tuple(int(n) for n in re.findall(r'\d+', cfi or ''))

def export_annotations(asset_id: str, format: str, book_title: str, book_author: str = "") -> str:
    """
    Exports annotations (highlights and notes) for the specified book to a file.

    Args:
        asset_id (str): The unique identifier for the book in the Apple Books library.
        format (str): The desired output format ('csv' or 'md').
        book_title (str): The title of the book.
        book_author (str): The author of the book.

    Returns:
        str: The name of the file where annotations were exported.

    Raises:
        ValueError: If an unsupported format is specified.
        sqlite3.Error: If there's an issue with the database connection or query.
        IOError: If there's an issue writing to the output file.
    """
    if format.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format! Please use one of: {', '.join(SUPPORTED_FORMATS)}")

    try:
        with sqlite3.connect(get_db_path(ANNOTATION_DB_PATTERN)) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT ZANNOTATIONSELECTEDTEXT, ZANNOTATIONNOTE, ZANNOTATIONLOCATION, ZANNOTATIONCREATIONDATE
                              FROM ZAEANNOTATION
                              WHERE ZANNOTATIONASSETID = ? AND ZANNOTATIONSELECTEDTEXT != "";''', (asset_id,))
            annotations = sorted(cursor.fetchall(), key=lambda row: cfi_sort_key(row[2]))
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise

    filename = f"highlights.{format.lower()}"

    try:
        if format.lower() == 'csv':
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["Chapter", "Highlight", "Notes", "Created"], delimiter=";")
                writer.writeheader()
                writer.writerows({"Chapter": parse_chapter_from_cfi(location),
                                  "Highlight": highlight.replace("\n", " "),
                                  "Notes": note.replace("\n", " ") if note else "",
                                  "Created": format_timestamp(ts) if ts else ""}
                                 for highlight, note, location, ts in annotations)
        else:  # markdown
            header = f"# {book_title}\n"
            if book_author:
                header += f"*{book_author}*\n"
            output_md = header + "\n"
            current_chapter = None
            for highlight, note, location, ts in annotations:
                chapter = parse_chapter_from_cfi(location)
                if chapter != current_chapter:
                    current_chapter = chapter
                    if chapter:
                        output_md += f"## {chapter}\n\n"
                output_md += "\n".join([f"> {line}" for line in highlight.split("\n")])
                output_md += "\n"
                if ts:
                    output_md += f"{format_timestamp(ts)}\n"
                output_md += "\n"
                if note:
                    output_md += f"{note}\n\n"

            with open(filename, 'w') as mdfile:
                mdfile.write(output_md)
            
    except IOError as e:
        logging.error(f"Error writing to file: {e}")
        raise

    return filename

def main():
    try:
        book_details = get_library_books()
        books = get_library_books_with_highlights()
    except (FileNotFoundError, sqlite3.Error) as e:
        logging.error(f"Error initializing: {e}")
        print("An error occurred while accessing the Apple Books database. Please ensure Apple Books is installed and you have the necessary permissions.")
        return

    selected_book: str = None
    selected_format: str = 'md'

    def get_main_menu_items() -> List[str]:
        return [
            f"Select Book (Current: {book_details[selected_book][0] if selected_book else 'None'})",
            f"Select Format (Current: {selected_format})",
            "Export Annotations",
            "Quit"
        ]

    main_menu_title = "BookBits - Apple Books Highlight Exporter"

    book_menu = TerminalMenu(
        [f"{book_details[book][0]} by {book_details[book][1]}" for book in books],
        title="Select a Book",
        menu_cursor=">> ",
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_red", "fg_black"),
    )

    format_menu = TerminalMenu(
        SUPPORTED_FORMATS,
        title="Select Output Format",
        menu_cursor=">> ",
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_red", "fg_black"),
    )

    while True:
        main_menu = TerminalMenu(
            get_main_menu_items(),
            title=main_menu_title,
            menu_cursor=">> ",
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_red", "fg_black"),
        )
        
        main_choice = main_menu.show()

        if main_choice == 0:  # Select Book
            book_choice = book_menu.show()
            if book_choice is not None:
                selected_book = books[book_choice]
        elif main_choice == 1:  # Select Format
            format_choice = format_menu.show()
            if format_choice is not None:
                selected_format = SUPPORTED_FORMATS[format_choice]
        elif main_choice == 2:  # Export Annotations
            if selected_book and selected_format:
                try:
                    filename = export_annotations(selected_book, selected_format, book_details[selected_book][0], book_details[selected_book][1])
                    print(f"Annotations exported to {filename}")
                    break
                except (ValueError, sqlite3.Error, IOError) as e:
                    print(f"Error exporting annotations: {e}")
            else:
                print("Please select a book before exporting!")
        elif main_choice == 3 or main_choice is None:  # Quit
            print("Exiting...")
            break

if __name__ == "__main__":
    main()