# IdleTypeCheck
Python IDLE extension to perform mypy analysis on an open file

<!-- BADGIE TIME -->

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/CoolCat467/idletypecheck/main.svg)](https://results.pre-commit.ci/latest/github/CoolCat467/idletypecheck/main)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![code style: black](https://img.shields.io/badge/code_style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<!-- END BADGIE TIME -->

## Notice
This project is superseded by my other IDLE extension,
[IdleMypyExtension](https://github.com/CoolCat467/idlemypyextension), which
uses the mypy daemon instead and has many more features.

## What does this extension do?
This IDLE extension hooks into mypy to type check the currently
open file. When type checking the currently open file with the
"Type Check File" command, it will add comments to your code wherever
mypy had something to say about about that line. You can remove type
comments from the currently selected text with the "Remove Type Comments"
command.
Additionally, you can jump to the next comment this extension created in
your file with the "Find Next Type Comment" command.

Note: On use, creates folder `mypy` within the idle user directory.
On Linux systems, this is usually `~/.idlerc/mypy`.

## Installation (Without root permissions)
1) Go to terminal and install with `pip install idletypecheck[user]`.
2) Run command `idleuserextend; idletypecheck`. You should see the following
output: `Config should be good! Config should be good!`.
3) Open IDLE, go to `Options` -> `Configure IDLE` -> `Extensions`.
If everything went well, alongside `ZzDummy` there should be and
option called `idletypecheck`. This is where you can configure how
idletypecheck works.

## Installation (Legacy, needs root permission)
1) Go to terminal and install with `pip install idletypecheck`.
2) Run command `idletypecheck`. You will likely see a message saying
`typecheck not in system registered extensions!`. Run the command
given to add lintcheck to your system's IDLE extension config file.
3) Again run command `typecheck`. This time, you should see the following
output: `Config should be good!`.
4) Open IDLE, go to `Options` -> `Configure IDLE` -> `Extensions`.
If everything went well, alongside `ZzDummy` there should be and
option called `idletypecheck`. This is where you can configure how
idletypecheck works.


## Information on options
For `extra_args`, see `mypy --help` for a list of valid flags.
This extension sets the following flags to be able to work properly:
```
    --hide-error-context
    --no-color-output
    --show-absolute-path
    --no-error-summary
    --soft-error-limit=-1
    --show-traceback
    --cache-dir="~/.idlerc/mypy"
```

If you add the `--show-column-numbers` flag to `extra_args`, when using the
"Type Check File" command, it will add a helpful little `^` sign
in a new line below the location of the mypy message that provided a column
number, as long as that comment wouldn't break your file's indentation too much.

If you add the `--show-error-codes` flag to `extra_args`, when using the
"Type Check File" command, when it puts mypy's comments in your code, it will
tell you what type of error that comment is. For example, it would change the
error comment
```python
# typecheck: error: Incompatible types in assignment (expression has type "str", variable has type "int")
```
to
```python
# typecheck: assignment error: Incompatible types in assignment (expression has type "str", variable has type "int")
```

`search_wrap` toggles weather searching for next type comment will wrap
around or not.
