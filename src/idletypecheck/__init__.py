#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Idle Type Check - Use mypy to type check open file, then add comments to file.

"Type Check IDLE Extension"

# Programmed by CoolCat467

from __future__ import annotations

__title__ = "idletypecheck"
__author__ = "CoolCat467"
__license__ = "GPLv3"
__version__ = "0.0.1"
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 1

import os
import re
import sys
from collections.abc import Callable
from functools import wraps
from idlelib import search, searchengine
from idlelib.config import idleConf
from idlelib.format import FormatRegion
from idlelib.iomenu import IOBinding
from idlelib.multicall import MultiCallCreator
from idlelib.pyshell import PyShellEditorWindow, PyShellFileList
from tkinter import Event, Tk, messagebox
from typing import Any, Final, TypeVar, cast

_HAS_MYPY = True
try:
    import mypy.api
except ImportError:
    print(f"{__file__}: Mypy not installed!")
    _HAS_MYPY = False


def get_required_config(
    values: dict[str, str], bind_defaults: dict[str, str]
) -> str:
    "Get required configuration file data"
    config = ""
    # Get configuration defaults
    settings = "\n".join(
        f"{key} = {default}" for key, default in values.items()
    )
    if settings:
        config += f"\n[{__title__}]\n{settings}"
        if bind_defaults:
            config += "\n"
    # Get key bindings data
    settings = "\n".join(
        f"{event} = {key}" for event, key in bind_defaults.items()
    )
    if settings:
        config += f"\n[{__title__}_cfgBindings]\n{settings}"
    return config


def check_installed() -> bool:
    "Make sure extension installed."
    # Get list of system extensions
    extensions = list(idleConf.defaultCfg["extensions"])
    ex_defaults = idleConf.defaultCfg["extensions"].file

    # Import this extension (this file),
    try:
        module = __import__(__title__)
    except ModuleNotFoundError:
        print(f"{__title__} is not installed!")
        return False

    # Get extension class
    if not hasattr(module, __title__):
        print(
            f"ERROR: Somehow, {__title__} was installed improperly, no {__title__} class "
            "found in module. Please report this on github.",
            file=sys.stderr,
        )
        sys.exit(1)

    cls = getattr(module, __title__)

    # Get extension class keybinding defaults
    required_config = get_required_config(
        getattr(cls, "values", {}), getattr(cls, "bind_defaults", {})
    )

    # If this extension not in there,
    if __title__ not in extensions:
        # Tell user how to add it to system list.
        print(f"{__title__} not in system registered extensions!")
        print(
            f"Please run the following command to add {__title__} to system extensions list.\n"
        )
        # Make sure line-breaks will go properly in terminal
        add_data = required_config.replace("\n", "\\n")
        # Tell them command
        print(f"echo -e '{add_data}' | sudo tee -a {ex_defaults}")
        print()
    else:
        print(f"Configuration should be good! (v{__version__})")
        return True
    return False


def get_line_selection(line: int) -> tuple[str, str]:
    "Get selection strings for given line"
    return f"{line}.0", f"{line+1}.0"


# Stolen from idlelib.searchengine
def get_line_col(index: str) -> tuple[int, int]:
    "Return (line, col) tuple of integers from 'line.col' string."
    line, col = map(int, index.split(".", 1))  # Fails on invalid index
    return line, col


def get_line_indent(text: str, char: str = " ") -> int:
    "Return line indent."
    for idx, cur in enumerate(text.split(char)):
        if cur != "":
            return idx
    return 0


def ensure_section_exists(section: str) -> bool:
    "Ensure section exists in user extensions configuration, return if edited"
    if not section in idleConf.GetSectionList("user", "extensions"):
        idleConf.userCfg["extensions"].AddSection(section)
        return True
    return False


F = TypeVar("F", bound=Callable[..., Any])


def undo_block(func: F) -> F:
    "Mark block of edits as a single undo block."

    @wraps(func)
    def undo_wrapper(self: "idletypecheck", *args: Any, **kwargs: Any) -> Any:
        "Wrap function in start and stop undo events."
        self.text.undo_block_start()
        try:
            return func(self, *args, **kwargs)
        finally:
            self.text.undo_block_stop()

    return cast(F, undo_wrapper)


def ensure_values_exist_in_section(
    section: str, values: dict[str, str]
) -> bool:
    """For each key in values, make sure key exists. Return if edited

    If not, create and set to value."""
    need_save = False
    for key, default in values.items():
        value = idleConf.GetOption(
            "extensions", section, key, warn_on_default=False
        )
        if value is None:
            idleConf.SetOption("extensions", section, key, default)
            need_save = True
    return need_save


def get_search_engine_params(
    engine: searchengine.SearchEngine,
) -> dict[str, str | bool]:
    "Get current search engine parameters"
    return {
        name: getattr(engine, f"{name}var").get()
        for name in ("pat", "re", "case", "word", "wrap", "back")
    }


def set_search_engine_params(
    engine: searchengine.SearchEngine, data: dict[str, str | bool]
) -> None:
    "Get current search engine parameters"
    for name in ("pat", "re", "case", "word", "wrap", "back"):
        if name in data:
            getattr(engine, f"{name}var").set(data[name])


# Important weird: If event handler function returns 'break',
# then it prevents other bindings of same event type from running.
# If returns None, normal and others are also run.


class idletypecheck:  # pylint: disable=invalid-name
    "Add comments from mypy to an open program."
    __slots__ = (
        "editwin",
        "text",
        "formatter",
        "files",
        "flist",
    )
    # Extend the file and format menus.
    menudefs = [
        (
            "edit",
            [
                None,
                ("_Type Check File", "<<type-check>>"),
                ("Find Next Type Comment", "<<find-next-type-comment>>"),
            ],
        ),
        ("format", [("Remove Type Comments", "<<remove-type-comments>>")]),
    ]
    # Default values for configuration file
    values = {
        "enable": "True",
        "enable_editor": "True",
        "enable_shell": "False",
        "extra_args": "None",
        "search_wrap": "False",
    }
    # Default key binds for configuration file
    bind_defaults = {
        "type-check": "<Alt-Key-t>",
        "remove-type-comments": "<Alt-Shift-Key-T>",
        "find-next-type-comment": "<Alt-Key-g>",
    }
    comment = "# typecheck: "

    # Overwritten in reload
    extra_args = "None"
    search_wrap = "False"

    # Class attributes
    idlerc_folder = os.path.expanduser(idleConf.userdir)
    mypy_folder = os.path.join(idlerc_folder, "mypy")

    def __init__(self, editwin: PyShellEditorWindow) -> None:
        "Initialize the settings for this extension."
        self.editwin: PyShellEditorWindow = editwin
        self.text: MultiCallCreator = editwin.text
        self.formatter: FormatRegion = editwin.fregion
        self.flist: PyShellFileList = editwin.flist
        self.files: IOBinding = editwin.io

        if not os.path.exists(self.mypy_folder):
            os.mkdir(self.mypy_folder)

        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            if attr_name.endswith("_event"):
                bind_name = "-".join(attr_name.split("_")[:-1]).lower()
                self.text.bind(f"<<{bind_name}>>", getattr(self, attr_name))
                # print(f'{attr_name} -> {bind_name}')

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.editwin!r})"

    @property
    def flags(self) -> list[str]:
        "Mypy flags"
        base = {
            f"--cache-dir={self.mypy_folder}",
            # "--cache-fine-grained",
            "--hide-error-context",
            "--no-color-output",
            "--show-absolute-path",
            "--no-error-summary",
            "--soft-error-limit=-1",
            "--show-traceback",
        }
        if self.extra_args == "None":
            return list(base)
        extra = set()
        for arg in self.extra_args.split(" "):
            value = arg.strip()
            if value:
                extra.add(value)
        return list(base | extra)

    @classmethod
    def ensure_bindings_exist(cls) -> bool:
        "Ensure key bindings exist in user extensions configuration. Return True if need to save."
        need_save = False
        section = f"{cls.__name__}_cfgBindings"
        if ensure_section_exists(section):
            need_save = True
        if ensure_values_exist_in_section(section, cls.bind_defaults):
            need_save = True
        return need_save

    @classmethod
    def ensure_config_exists(cls) -> bool:
        "Ensure required configuration exists for this extension. Return True if need to save."
        need_save = False
        if ensure_section_exists(cls.__name__):
            need_save = True
        if ensure_values_exist_in_section(cls.__name__, cls.values):
            need_save = True
        return need_save

    @classmethod
    def reload(cls) -> None:
        "Load class variables from configuration."
        # # Ensure file default values exist so they appear in settings menu
        # save = cls.ensure_configuration_exists()
        # if cls.ensure_bindings_exist() or save:
        #     idleConf.SaveUserCfgFiles()

        # Reload configuration file
        idleConf.LoadCfgFiles()

        # For all possible configuration values
        for key, default in cls.values.items():
            # Set attribute of key name to key value from configuration file
            if not key in {"enable", "enable_editor", "enable_shell"}:
                value = idleConf.GetOption(
                    "extensions", cls.__name__, key, default=default
                )
                setattr(cls, key, value)

    @classmethod
    def get_msg_line(cls, indent: int, msg: str) -> str:
        "Return message line given indent and message."
        strindent = " " * indent
        return f"{strindent}{cls.comment}{msg}"

    def get_line(self, line: int) -> str:
        "Get the characters from the given line in the currently open file."
        chars: str = self.text.get(*get_line_selection(line))
        return chars

    def comment_exists(self, line: int, text: str) -> bool:
        "Return True if comment for message already exists on line."
        return self.get_msg_line(0, text) in self.get_line(line - 1)

    def add_comment(
        self, message: dict[str, str | int], max_exist_up: int = 0
    ) -> bool:
        "Return True if added new comment, False if already exists."
        # Get line and message from output
        # file = str(message['file'])
        line = int(message["line"])
        msg = str(message["message"])

        # If there is already a comment from us there, ignore that line.
        # +1-1 is so at least up by 1 is checked, range(0) = []
        for i in range(max_exist_up + 1):
            if self.comment_exists(line - (i - 1), msg):
                return False

        # Get line checker is talking about
        chars = self.get_line(line)

        # Figure out line indent
        indent = get_line_indent(chars)

        # Add comment line
        chars = self.get_msg_line(indent, msg) + "\n" + chars

        # Save changes
        start, end = get_line_selection(line)
        self.text.delete(start, end)
        self.text.insert(start, chars, ())
        return True

    @staticmethod
    def parse_comments(
        comments: str, default_file: str, default_line: int
    ) -> dict[str, list[dict[str, str | int]]]:
        "Get list of message dictionaries from mypy output."
        error_type = re.compile(r"  \[[a-z\-]+\]\s*$")

        files: dict[str, list[dict[str, str | int]]] = {}
        for comment in comments.splitlines():
            filename = default_file
            line = default_line
            line_end = default_line
            col = 0
            col_end = 0
            mtype = "unrecognized"

            if comment.count(": ") < 2:
                text = comment
            else:
                where, mtype, text = comment.split(": ", 2)

                position = where.split(":")

                filename = position[0]
                if len(position) > 1:
                    line = int(position[1])
                    line_end = line
                if len(position) > 2:
                    col = int(position[2])
                    col_end = col
                if len(position) > 4:
                    line_end = int(position[3])
                    if line_end == line:
                        col_end = int(position[4])
                    else:
                        line_end = line
            comment_type = error_type.search(text)
            if comment_type is not None:
                text = text[: comment_type.start()]
                mtype = f"{comment_type.group(0)[3:-1]} {mtype}"

            message: dict[str, str | int] = {
                "file": filename,
                "line": line,
                "column": col,
                "line_end": line_end,
                "column_end": col_end,
                "type": mtype,
                "message": f"{mtype}: {text}",
            }

            if not filename in files:
                files[filename] = []
            files[filename].append(message)
        return files

    def get_pointers(
        self, messages: list[dict[str, int | str]]
    ) -> dict[str, int | str] | None:
        "Return message pointing to message column position"
        line = int(messages[0]["line"]) + 1

        # Figure out line intent
        line_text = self.get_line(line)
        indent = get_line_indent(line_text)
        line_len = len(line_text)

        columns: set[int] = set()
        lastcol = len(self.comment) + indent + 1

        for message in messages:
            start = int(message["column"])
            end = int(message.get("column_end", start + lastcol)) - lastcol
            for col in range(start, end + 1):
                columns.add(col)

        new_line = ""
        for col in sorted(columns):
            if col > line_len:
                break
            spaces = col - lastcol - 1
            new_line += " " * spaces + "^"
            lastcol = col

        if not new_line.strip():
            return None

        return {"line": line, "message": new_line}

    def add_comments(
        self, target_filename: str, start_line: int, normal: str
    ) -> list[int]:
        "Add comments for target filename, return list of comments added"
        files = self.parse_comments(
            normal, os.path.abspath(self.files.filename), start_line
        )

        # Only handling messages for target filename
        line_data: dict[int, list[dict[str, Any]]] = {}
        if target_filename in files:
            for message in files[target_filename]:
                line = message["line"]
                assert isinstance(line, int), "Line must be int"
                if not line in line_data:
                    line_data[line] = []
                line_data[line].append(message)

        line_order: list[int] = list(sorted(line_data, reverse=True))
        first: int = line_order[-1] if line_order else start_line

        if not first in line_data:  # if used starting line
            line_data[first] = []
            line_order.append(first)

        for filename in {f for f in files if f != target_filename}:
            line_data[first].append(
                {
                    "file": target_filename,
                    "line": first,
                    "column": 0,
                    "column_end": 0,
                    "type": "note",
                    "message": f"Another file has errors: {filename}",
                }
            )

        comments = []
        for line in line_order:
            messages = line_data[line]
            if not messages:
                continue
            pointers = self.get_pointers(messages)
            if pointers is not None:
                messages.append(pointers)

            total = len(messages)
            for message in reversed(messages):
                if self.add_comment(message, total):
                    comments.append(line)
        return comments

    def ask_save_dialog(self) -> bool:
        "Ask to save dialog stolen from idlelib.runscript.ScriptBinding"
        msg = "Source Must Be Saved\n" + 5 * " " + "OK to Save?"
        confirm: bool = messagebox.askokcancel(
            title="Save Before Run or Check",
            message=msg,
            default=messagebox.OK,
            parent=self.text,
        )
        return confirm

    def initial(self) -> tuple[str | None, str, int]:
        """Do common initial setup. Return error or none, file, and start line

        Reload configuration, make sure file is saved,
        and make sure mypy is installed"""
        self.reload()

        # Get file we are checking
        file: str = os.path.abspath(self.files.filename)

        # Remember where we started
        start_line_no: int = self.editwin.getlineno()

        if not _HAS_MYPY:
            self.add_comment(
                {
                    "file": file,
                    "line": start_line_no,
                    "message": "Could not import mypy. "
                    "Please install mypy and restart IDLE to use this extension.",
                },
                start_line_no,
            )

            # Make bell sound so user knows they need to pay attention
            self.text.bell()
            return "break", file, start_line_no

        # Make sure file is saved.
        if not self.files.get_saved():
            if not self.ask_save_dialog():
                # If not ok to save, do not run. Would break file.
                self.text.bell()
                return "break", file, start_line_no
            # Otherwise, we are clear to save
            self.files.save(None)
            self.files.set_saved(True)

        # Everything worked
        return None, file, start_line_no

    @undo_block
    def type_check_event(self, event: "Event[Any]") -> str:
        "Preform a mypy check and add comments."
        # pylint: disable=unused-argument
        init_return, file, start_line_no = self.initial()

        if init_return is not None:
            return init_return

        # Run mypy on open file
        normal, errors = mypy.api.run(  # pylint: disable=c-extension-no-member
            self.flags
        )[:-1]

        if errors:
            lines = errors.splitlines()
            lines[0] = f"Error running mypy: {lines[0]}"
            for message in reversed(lines):
                self.add_comment(
                    {
                        "file": file,
                        "line": start_line_no,
                        "message": message,
                    },
                    len(lines),
                )

            self.text.bell()
            return "break"

        if normal:
            # Add code comments
            self.add_comments(file, start_line_no, normal)

        # Make bell sound so user knows we are done,
        # as it freezes a bit while mypy looks at the file
        self.text.bell()
        return "break"

    def remove_type_comments_event(self, event: Event[Any]) -> str:
        "Remove selected mypy comments."
        # pylint: disable=unused-argument
        # Get selected region lines
        head, tail, chars, lines = self.formatter.get_region()
        if not self.comment in chars:
            # Make bell sound so user knows this ran even though
            # nothing happened.
            self.text.bell()
            return "break"
        # Using dict so we can reverse and enumerate
        ldict = dict(enumerate(lines))
        for idx in sorted(ldict.keys(), reverse=True):
            line = ldict[idx]
            # If after indent there is mypy comment
            if line.lstrip().startswith(self.comment):
                # If so, remove line
                del lines[idx]
        # Apply changes
        self.formatter.set_region(head, tail, chars, lines)
        return "break"

    @undo_block
    def remove_all_type_comments(self, event: Event[Any]) -> str:
        "Remove all mypy comments."
        # pylint: disable=unused-argument
        eof_idx = self.text.index("end")

        chars = self.text.get("0.0", eof_idx)

        lines = chars.splitlines()
        modified = False
        for idx in reversed(range(len(lines))):
            if lines[idx].lstrip().startswith(self.comment):
                del lines[idx]
                modified = True
        if not modified:
            return "break"

        chars = "\n".join(lines)

        # Apply changes
        self.text.delete("0.0", eof_idx)
        self.text.insert("0.0", chars, None)
        return "break"

    @undo_block
    def find_next_type_comment_event(self, event: "Event[Any]") -> str:
        "Find next comment by hacking the search dialog engine."
        # pylint: disable=unused-argument
        self.reload()

        root: Tk
        root = self.text._root()  # pylint: disable=protected-access

        # Get search engine singleton from root
        engine: searchengine.SearchEngine = searchengine.get(root)

        # Get current search prams
        global_search_params = get_search_engine_params(engine)

        # Set search pattern to comment starter
        set_search_engine_params(
            engine,
            {
                "pat": f"^\\s*{self.comment}",
                "re": True,
                "case": True,
                "word": False,
                "wrap": self.search_wrap == "True",
                "back": False,
            },
        )

        # Find current pattern
        search.find_again(self.text)

        # Re-apply previous search prams
        set_search_engine_params(engine, global_search_params)
        return "break"


idletypecheck.reload()

if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    check_installed()
