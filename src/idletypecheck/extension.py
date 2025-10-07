"""Type Check IDLE Extension."""

# Programmed by CoolCat467

from __future__ import annotations

# Idle Type Check - Use mypy to type check open file, then add comments to file.
# Copyright (C) 2023-2025  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "extension"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"

import os
import re
import sys
from idlelib.config import idleConf
from idlelib.pyshell import PyShellEditorWindow
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

import mypy.api

from idletypecheck import utils

if TYPE_CHECKING:
    from collections.abc import Sequence
    from idlelib.pyshell import PyShellEditorWindow
    from tkinter import Event


UNKNOWN_FILE: Final = "<unknown file>"
MYPY_ERROR_TYPE: Final = re.compile(r"  \[([a-z\-]+)\]\s*$")


def debug(message: object) -> None:
    """Print debug message."""
    # TODO: Censor username/user files
    print(f"\n[{__name__}] DEBUG: {message}")


def parse_comments(
    mypy_output: str,
    default_file: str = "<unknown file>",
    default_line: int = 0,
) -> dict[str, list[utils.Comment]]:
    """Parse mypy output, return mapping of filenames to lists of comments."""
    files: dict[str, list[utils.Comment]] = {}
    for output_line in mypy_output.splitlines():
        if not output_line.strip():
            continue
        filename = default_file
        line = default_line
        line_end = default_line
        col = 0
        col_end = 0
        msg_type = "unrecognized"

        if output_line.count(": ") < 2:
            text = output_line
        else:
            where, msg_type, text = output_line.split(": ", 2)

            windows_drive_letter = ""
            if sys.platform == "win32":
                windows_drive_letter, where = where.split(":", 1)
                windows_drive_letter += ":"
            position = where.rsplit(":", 4)

            filename = f"{windows_drive_letter}{position[0]}"
            colon_count = len(position)
            if colon_count > 1:
                line = int(position[1])
                line_end = line
            if colon_count > 2:
                col = int(position[2])
                col_end = col
            if colon_count > 4:
                line_end = int(position[3])
                # if line_end == line:
                col_end = int(position[4])
                # else:
                #    line_end = line
        comment_type = MYPY_ERROR_TYPE.search(text)
        if comment_type is not None:
            text = text[: comment_type.start()]
            msg_type = f"{comment_type.group(1)} {msg_type}"

        comment = utils.Comment(
            file=filename,
            line=line,
            contents=f"{msg_type}: {text}",
            column=col,
            line_end=line_end,
            column_end=col_end,
        )

        files.setdefault(filename, [])
        files[filename].append(comment)
    return files


# Important weird: If event handler function returns 'break',
# then it prevents other bindings of same event type from running.
# If returns None, normal and others are also run.


class idletypecheck(utils.BaseExtension):  # noqa: N801
    """Add comments from mypy to an open program."""

    __slots__ = ()
    # Extend the file and format menus.
    menudefs: ClassVar[
        Sequence[tuple[str, Sequence[tuple[str, str] | None]]]
    ] = (
        (
            "edit",
            (
                None,
                ("_Type Check File", "<<type-check>>"),
                ("Find Next Type Comment", "<<find-next-type-comment>>"),
            ),
        ),
        (
            "format",
            (("Remove Type Comments", "<<remove-type-comments>>"),),
        ),
    )
    # Default values for configuration file
    values: ClassVar = {
        "enable": "True",
        "enable_editor": "True",
        "enable_shell": "False",
        "extra_args": "None",
        "search_wrap": "False",
    }
    # Default key binds for configuration file
    bind_defaults: ClassVar = {
        "type-check": "<Alt-Key-t>",
        "remove-type-comments": "<Alt-Shift-Key-T>",
        "find-next-type-comment": "<Alt-Key-g>",
    }

    # Overwritten in reload
    extra_args = "None"
    search_wrap = "False"

    # Class attributes
    idlerc_folder = Path(idleConf.userdir).expanduser().absolute()
    mypy_folder = idlerc_folder / "mypy"

    def __init__(self, editwin: PyShellEditorWindow) -> None:
        """Initialize the settings for this extension."""
        super().__init__(editwin, comment_prefix="typecheck")

        if not os.path.exists(self.mypy_folder):
            os.mkdir(self.mypy_folder)

    @property
    def flags(self) -> list[str]:
        """Mypy flags."""
        base = {
            "--hide-error-context",
            "--no-color-output",
            "--show-absolute-path",
            "--no-error-summary",
            "--soft-error-limit=-1",
            "--show-traceback",
            f'--cache-dir="{self.mypy_folder}"',
            # f'--log-file="{self.log_file}"',
            # "--cache-fine-grained",
        }
        if self.extra_args == "None":
            return list(base)
        extra = set()
        for arg in self.extra_args.split():
            value = arg.strip()
            if value:
                extra.add(value)
        return list(base | extra)

    @property
    def typecomment_only_current_file(self) -> bool:
        """Should only add type comments for currently open file?."""
        return True

    def add_type_comments_for_file(
        self,
        comments: list[utils.Comment],
    ) -> dict[str, list[int]]:
        """Add type comments for target files.

        Return list of lines were a comment was added.

        Changes are wrapped in an undo block.
        """
        # Split up comments by line in order
        line_data: dict[int, list[utils.Comment]] = {}
        for comment in comments:
            line_data.setdefault(comment.line, [])
            line_data[comment.line].append(comment)

        all_messages = []
        for line in sorted(line_data):
            messages = line_data[line]
            if not messages:
                continue
            all_messages.extend(messages)
            pointers = self.get_pointers(messages)
            if pointers is not None:
                all_messages.append(pointers)

        return self.add_comments(all_messages)

    def add_mypy_messages(
        self,
        start_line: int,
        mypy_output: str,
        only_filename: str | None = None,
        add_all_override: bool = False,
    ) -> dict[str, list[int]]:
        """Add mypy comments for target filename.

        Return list of lines where comments were added.

        Changes are wrapped in an undo block.
        """
        default_file = UNKNOWN_FILE
        if self.files.filename is not None:
            default_file = os.path.abspath(self.files.filename)

        if only_filename is not None:
            only_filename = os.path.abspath(only_filename)

        file_comments = parse_comments(
            mypy_output,
            default_file,
            start_line,
        )

        file_commented_lines: dict[str, list[int]] = {}

        to_comment = set(file_comments)

        if self.typecomment_only_current_file and not add_all_override:
            assert only_filename is not None
            to_comment = {only_filename}

            # Find first line in target file or use start_line
            if not file_comments.get(only_filename):
                other_files_comment_line = start_line
            else:
                other_files_comment_line = min(
                    comment.line for comment in file_comments[only_filename]
                )

            # Add comments about how other files have errors
            file_comments.setdefault(only_filename, [])
            for filename in file_comments:
                if filename == only_filename:
                    continue
                file_comments[only_filename].append(
                    utils.Comment(
                        file=only_filename,
                        line=other_files_comment_line,
                        contents=f"Another file has errors: {filename!r}",
                        column_end=0,
                    ),
                )

        for target_filename in to_comment:
            if target_filename not in file_comments:
                continue
            if target_filename == UNKNOWN_FILE:
                continue
            file_comment_lines = self.add_type_comments_for_file(
                file_comments[target_filename],
            )
            file_commented_lines.update(file_comment_lines)
        return file_commented_lines

    def add_extra_data(
        self,
        file: str,
        start_line: int,
        data: str,
        prefix: str = "",
    ) -> tuple[int, list[int]]:
        """Add extra data to file as a big block of comments.

        Returns
        -------
        Tuple of:
        - Number of lines attempted to add
        - List of line numbers added that were not already there
        otherwise empty because no content.

        Changes are wrapped in an undo block.

        """
        if not data:
            return 0, []
        lines = data.splitlines()
        if not lines:
            return 0, []
        lines[0] = f"{prefix}{lines[0]}"
        added = self.add_comment_block(file, start_line, lines)
        return len(lines), added

    def add_errors(
        self,
        file: str,
        start_line: int,
        errors: str,
    ) -> tuple[int, list[int]]:
        """Add error lines to file as a block of comments.

        Returns
        -------
        Tuple of:
        - Number of lines attempted to add
        - List of line numbers added that were not already there
        otherwise None because no content.

        """
        return self.add_extra_data(
            file,
            start_line,
            errors,
            prefix="Error running mypy: ",
        )

    def check(self, file: str) -> tuple[str, str, int]:
        """Perform mypy run.

        Returns (normal_report, error_report, exit_status).
        """
        flags = self.flags
        flags += [file]
        command = " ".join(
            [
                "mypy",
                *self.flags,
                f'"{file}"',
            ],
        )
        debug(f"{command = }")
        normal_report, error_report, exit_status = mypy.api.run(flags)
        return (normal_report, error_report, exit_status)

    def initial(self) -> tuple[str | None, str | None]:
        """Do common initial setup. Return error or none, file.

        Reload configuration, make sure file is saved,
        and make sure mypy is installed
        """
        # Reload configuration
        self.reload()

        # Get file we are checking
        raw_filename: str | None = self.files.filename
        if raw_filename is None:
            return "break", None
        file: str = os.path.abspath(raw_filename)

        # Make sure file is saved.
        if not self.files.get_saved():
            if not utils.ask_save_dialog(self.text):
                # If not ok to save, do not run. Would break file.
                self.text.bell()
                return "break", file
            # Otherwise, we are clear to save
            self.files.save(None)
            if not self.files.get_saved():
                return "break", file

        # Everything worked
        return None, file

    def type_check_add_response_comments(
        self,
        response: tuple[str, str, int],
        file: str,
    ) -> int:
        """Add all the comments (normal and error) from mypy response.

        Return mypy's exit status.
        """
        debug(f"type check {response = }")
        normal_report, error_report, exit_status = response

        if normal_report:
            # Add code comments
            self.add_mypy_messages(
                self.editwin.getlineno(),
                normal_report,
                file,
            )
        if error_report:
            self.add_errors(file, self.editwin.getlineno(), error_report)

        # Make bell sound so user knows we are done,
        # as it freezes a bit while mypy looks at the file
        self.text.bell()

        return exit_status

    def type_check_event(self, event: Event[Any]) -> str:
        """Perform a mypy check and add comments."""
        init_return, file = self.initial()

        if init_return is not None:
            return init_return

        if file is None:
            return "break"

        # Run mypy on open file
        response = self.check(file)

        self.type_check_add_response_comments(response, file)
        return "break"

    def remove_type_comments_event(self, _event: Event[Any]) -> str:
        """Remove selected extension comments."""
        self.remove_selected_extension_comments()
        return "break"

    def remove_all_type_comments(self, _event: Event[Any]) -> str:
        """Remove all extension comments."""
        self.remove_all_extension_comments()
        return "break"

    def find_next_type_comment_event(self, event: Event[Any]) -> str:
        """Find next extension comment by hacking the search dialog engine."""
        # Reload configuration
        self.reload()

        # Find comment
        self.find_next_extension_comment(self.search_wrap == "True")

        return "break"

    # def close(self) -> None:
    #    """Called when any idle editor window closes"""
