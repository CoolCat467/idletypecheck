#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Idle Type Check - Use mypy to type check open file, then add comments to file.

"Type Check IDLE Extension"

# Programmed by CoolCat467

from __future__ import annotations

__title__     = 'idletypecheck'
__author__    = 'CoolCat467'
__license__   = 'GPLv3'
__version__   = '0.0.0'
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 0

from typing import Any, Callable, TypeVar, cast

import os
import sys
from functools import wraps
from tkinter   import messagebox, Event, Tk

from idlelib         import search, searchengine # type: ignore
from idlelib.config  import idleConf             # type: ignore
from idlelib.pyshell import PyShellEditorWindow  # type: ignore

_HAS_MYPY = True
try:
    import mypy.api
except ImportError:
    print(f'{__file__}: Mypy not installed!')
    _HAS_MYPY = False

def check_installed() -> bool:
    "Make sure extension installed."
    # Get list of system extensions
    extensions = list(idleConf.defaultCfg['extensions'])
    # If this extension not in there,
    if __title__ not in extensions:
        # Tell user how to add it to system list.
        print(f'{__title__} not in system registered extensions!')
        print(f'Please run the following command to add {__title__} to system extensions list.\n')
        ex_defaults = idleConf.defaultCfg['extensions'].file

        # Import this extension (this file),
        try:
            module = __import__(__title__)
        except ModuleNotFoundError:
            print(f'{__title__} is not installed!')
            return False
        # Get extension class
        if hasattr(module, __title__):
            cls = getattr(module, __title__)
            # Get extension class keybinding defaults
            add_data = ''
            if hasattr(cls, 'values'):
                # Get configuration defaults
                values = '\n'.join(f'{key} = {default}' for key, default in cls.values.items())
                # Add to add_data
                add_data += f"\n[{__title__}]\n{values}"
            if hasattr(cls, 'bind_defaults'):
                # Get keybindings data
                values = '\n'.join(f'{event} = {key}' for event, key in cls.bind_defaults.items())
                # Add to add_data
                add_data += f"\n[{__title__}_cfgBindings]\n{values}"
            # Make sure line-breaks will go properly in terminal
            add_data = add_data.replace('\n', '\\n')
            # Tell them command
            print(f"echo -e '{add_data}' | sudo tee -a {ex_defaults}")
            print()
        else:
            print(f'ERROR: Somehow, {__title__} was installed improperly, no {__title__} class '\
                  'found in module. Please report this on github.', file=sys.stderr)
            sys.exit(1)
    else:
        print(f'Configuration should be good! (v{__version__})')
        return True
    return False

def get_line_selection(line: int) -> tuple[str, str]:
    "Get selection strings for given line"
    return f'{line}.0', f'{line+1}.0'

def get_line_indent(text: str, char: str=' ') -> int:
    "Return line indent."
    for idx, cur in enumerate(text.split(char)):
        if cur != '':
            return idx
    return 0

def ensure_section_exists(section: str) -> bool:
    "Ensure section exists in user extensions configuration. Return True if created."
    if not section in idleConf.GetSectionList('user', 'extensions'):
        idleConf.userCfg['extensions'].AddSection(section)
        return True
    return False

F = TypeVar('F', bound=Callable[..., Any])

def undo_block(func: F) -> F:
    "Mark block of edits as a single undo block."
    @wraps(func)
    def undo_wrapper(self: 'idletypecheck', *args: Any, **kwargs: Any) -> Any:
        "Wrap function in start and stop undo events."
        self.text.undo_block_start()
        result = func(self, *args, **kwargs)
        self.text.undo_block_stop()
        return result
    return cast(F, undo_wrapper)

def ensure_values_exist_in_section(section: str, values: dict[str, str]) -> bool:
    "For each key in values, make sure key exists. If not, create and set to value. "\
    "Return True if created any defaults."
    need_save = False
    for key, default in values.items():
        value = idleConf.GetOption('extensions', section, key,
                                   warn_on_default=False)
        if value is None:
            idleConf.SetOption('extensions', section, key, default)
            need_save = True
    return need_save

def get_search_engine_params(engine: searchengine.SearchEngine) -> dict[str, str | bool]:
    "Get current search engine parameters"
    return {
        name: getattr(engine, f'{name}var').get()
        for name in ('pat', 're', 'case', 'word', 'wrap', 'back')
    }

def set_search_engine_params(engine: searchengine.SearchEngine,
                             data: dict[str, str | bool]) -> None:
    "Get current search engine parameters"
    for name in ('pat', 're', 'case', 'word', 'wrap', 'back'):
        if name in data:
            getattr(engine, f'{name}var').set(data[name])

# Important weird: If event handler function returns 'break',
# then it prevents other bindings of same event type from running.
# If returns None, normal and others are also run.

class idletypecheck:# pylint: disable=invalid-name
    "Add comments from mypy to an open program."
    __slots__ = (
        'editwin',
        'text',
        'formatter',
        'files',
        'flist',
        'mypy_folder'
    )
    # Extend the file and format menus.
    menudefs = [
        ('edit', [
            None,
            ('_Type Check File', '<<type-check>>'),
            ('Find Next Type Comment', '<<find-next-type-comment>>')
        ] ),
        ('format', [
            ('Remove Type Comments', '<<remove-type-comments>>')
        ] )
    ]
    # Default values for configuration file
    values = {
        'enable'       : 'True',
        'enable_editor': 'True',
        'enable_shell' : 'False',
        'extra_args'   : 'None',
        'search_wrap'  : 'False'
    }
    # Default keybinds for configuration file
    bind_defaults = {
        'type-check'            : '<Alt-Key-t>',
        'remove-type-comments'  : '<Alt-Shift-Key-T>',
        'find-next-type-comment': '<Alt-Key-g>'
    }
    comment = '# typecheck: '

    # Overwritten in reload
    extra_args = 'None'
    search_wrap = 'False'

    def __init__(self, editwin: PyShellEditorWindow) -> None:
        "Initialize the settings for this extension."
##        self.editwin  : idlelib.pyshell.PyShellEditorWindow = editwin
##        self.text     : idlelib.multicall.MultiCallCreator  = editwin.text
##        self.formatter: idlelib.format.FormatRegion         = editwin.fregion
####        self.flist    : idlelib.pyshell.PyShellFileList     = editwin.flist
##        self.files    : idlelib.iomenu.IOBinding            = editwin.io
        self.editwin   = editwin
        self.text      = editwin.text
        self.formatter = editwin.fregion
        self.flist     = editwin.flist
        self.files     = editwin.io

        self.mypy_folder = os.path.expanduser(
            os.path.join(idleConf.userdir, 'mypy')
        )
        if not os.path.exists(self.mypy_folder):
            os.mkdir(self.mypy_folder)

        for attrname in (a for a in dir(self) if not a.startswith('_')):
            if attrname.endswith('_event'):
                bind_name = '_'.join(attrname.split('_')[:-1]).lower()
                self.text.bind(f'<<{bind_name}>>', getattr(self, attrname))
##                print(f'{attrname} -> {bind_name}')

    @classmethod
    def ensure_bindings_exist(cls) -> bool:
        "Ensure key bindings exist in user extensions configuration. Return True if need to save."
        need_save = False
        section = f'{cls.__name__}_cfgBindings'
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
##        # Ensure file default values exist so they appear in settings menu
##        save = cls.ensure_config_exists()
##        if cls.ensure_bindings_exist() or save:
##            idleConf.SaveUserCfgFiles()
        # For all possible configuration values
        for key, default in cls.values.items():
            # Set attribute of key name to key value from configuration file
            if not key in {'enable', 'enable_editor', 'enable_shell'}:
                value = idleConf.GetOption(
                    'extensions',
                    cls.__name__,
                    key,
                    default=default
                )
                setattr(cls, key, value)

    def get_msg_line(self, indent: int, msg: str) -> str:
        "Return message line given indent and message."
        strindent = ' '*indent
        return f'{strindent}{self.comment}{msg}'

    def get_line(self, line: int) -> str:
        "Get the characters from the given line in the currently open file."
        chars: str = self.text.get(*get_line_selection(line))
        return chars

    def comment_exists(self, line: int, text: str) -> bool:
        "Return True if comment for message already exists on line."
        return self.get_msg_line(0, text) in self.get_line(line-1)

    def add_comment(self,
                    message: dict[str, str | int],
                    max_exist_up: int = 0) -> bool:
        "Return True if added new comment, False if already exists."
        # Get line and message from output
##        file = str(message['file'])
        line = int(message['line'])
        msg  = str(message['message'])

        # If there is already a comment from us there, ignore that line.
        # +1-1 is so at least up by 1 is checked, range(0) = []
        for i in range(max_exist_up+1):
            if self.comment_exists(line-(i-1), msg):
                return False

        # Get line checker is talking about
        chars = self.get_line(line)

        # Figure out line indent
        indent = get_line_indent(chars)

        # Add comment line
        chars = self.get_msg_line(indent, msg)+'\n'+chars

        # Save changes
        start, end = get_line_selection(line)
        self.text.delete(start, end)
        self.text.insert(start, chars, None)
        return True

    def add_comments(self,
                     target_filename: str,
                     normal: str,
                     error: str) -> list[int]:
        "Add comments for target filename, return list of comments added"
        files: dict[str, list[dict[str, Any]]] = {}
        start_line = self.editwin.getlineno()
        for comment in error.splitlines() + normal.splitlines():
            filename: str
            message: dict[str, Any]
            if not comment.count(':') >= 3:
                filename = os.path.abspath(self.files.filename)
                message = {
                    'file': filename,
                    'line': start_line,
                    'type': 'other',
                    'message': comment
                }
            else:
                data = comment.split(':', 3)
                # fix type, ex. ' error' -> 'error'
                for i in range(2, len(data)):
                    data[i] = data[i][1:]

                filename = os.path.abspath(data[0])
                message = {
                    'file': filename,
                    'line': int(data[1]),
                    'type': data[2],
                    'message': f'{data[2]}: {data[3]}'
                }

                if not filename in files:
                    files[filename] = []
                files[filename].append(message)

        # Only handling messages for target filename
        line_data: dict[int, list] = {}
        if target_filename in files:
            for message in files[target_filename]:
                line: int = message['line']
                if not line in line_data:
                    line_data[line] = []
                line_data[line].append(message)

        line_order: list[int] = list(sorted(line_data, reverse=True))
        first: int = line_order[-1] if line_order else start_line

        if not first in line_data:# if used starting line
            line_data[first] = []
            line_order.append(first)

        for filename in {f for f in files if f != target_filename}:
            line_data[first].append({
                'file': target_filename,
                'line': first,
                'type': 'note',
                'message': f'Another file has errors: {filename}'
            })

        comments = []
        for line in line_order:
            messages = line_data[line]

            order = ['error', 'note']
            for msg in messages:
                if not msg['type'] in order:
                    order.append(msg['type'])

            ordered = []
            for msg_type in reversed(order):
                for msg in messages:
                    if msg['type'] == msg_type:
                        ordered.append(msg)

            total = len(ordered)
            for message in ordered:
                if self.add_comment(message, total):
                    comments.append(line)
        return comments

    def ask_save_dialog(self) -> bool:
        "Ask to save dialog stolen from idlelib.runscript.ScriptBinding"
        msg = 'Source Must Be Saved\n' + 5*' ' + 'OK to Save?'
        confirm: bool = messagebox.askokcancel(
            title   = 'Save Before Run or Check',
            message = msg,
            default = messagebox.OK,
            parent  = self.text
        )
        return confirm

    @undo_block
    def type_check_event(self, event: Event) -> str:
        "Preform a mypy check and add comments."
        self.reload()

        # Get file we are checking
        file: str = os.path.abspath(self.files.filename)

        # Remember where we started
        start_line_no: int = self.editwin.getlineno()

        if not _HAS_MYPY:
            self.add_comment({
                'file': file,
                'line': start_line_no,
                'message': 'Could not import mypy. '\
                'Please install mypy and restart IDLE to use this extension.'
            }, start_line_no)

            # Make bell sound so user knows they need to pay attention
            self.text.bell()
            return 'break'

        # Make sure file is saved.
        if not self.files.get_saved():
            if not self.ask_save_dialog():
                # If not ok to save, do not run. Would break file.
                self.text.bell()
                return 'break'
            # Otherwise, we are clear to save
            self.files.save(event)

        # Get arguments
        args = [file, '--cache-dir', self.mypy_folder]
        if self.extra_args != 'None':
            if ' ' in self.extra_args:
                args += self.extra_args.split(' ')
            else:
                args.append(self.extra_args)

        # Run mypy on open file
        normal, errors, file_count = mypy.api.run(args)# pylint: disable=c-extension-no-member

        if file_count:
            # Add code comments
            self.add_comments(file, normal, errors)

        # Make bell sound so user knows we are done,
        # as it freezes a bit while mypy looks at the file
        self.text.bell()
        return 'break'

    def remove_type_comments_event(self, event: Event) -> str:
        "Remove selected mypy comments."
        # Get selected region lines
        head, tail, chars, lines = self.formatter.get_region()
        if not self.comment in chars:
            # Make bell sound so user knows this ran even though
            # nothing happened.
            self.text.bell()
            return 'break'
        # Using dict so we can reverse and enumerate
        ldict = dict(enumerate(lines))
        for idx in sorted(ldict.keys(), reverse=True):
            line = ldict[idx]
            # Get line indent, see if after indent there is mypy comment
            indent = get_line_indent(line)
            if line[indent:].startswith(self.comment):
                # If so, remove line
                del lines[idx]
        # Apply changes
        self.formatter.set_region(head, tail, chars, lines)
        return 'break'

    def find_next_type_comment_event(self, event: Event) -> str:
        "Find next comment by hacking the search dialog engine."
        self.reload()

        root: Tk
        root = self.text._root()# type: ignore # pylint: disable=protected-access

        # Get search engine singleton from root
        engine: searchengine.SearchEngine = searchengine.get(root)

        # Get current search prams
        global_search_params = get_search_engine_params(engine)

        # Set search pattern to comment starter
        set_search_engine_params(engine, {
            'pat' : f'\s*{self.comment}',# pylint: disable=anomalous-backslash-in-string
            're'  : True,
            'case': True,
            'word': False,
            'wrap': self.search_wrap == 'True',
            'back': False
        })

        # Find current pattern
        search.find_again(self.text)

        # Re-apply previous search prams
        set_search_engine_params(engine, global_search_params)
        return 'break'

idletypecheck.reload()

if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.\n')
    check_installed()
