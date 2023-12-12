# IdleTypeCheck
Python IDLE extension to perform mypy analysis on an open file

<!-- BADGIE TIME -->

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![code style: black](https://img.shields.io/badge/code_style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<!-- END BADGIE TIME -->

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
2) Run command `typecheck`. You will likely see a message saying
`typecheck not in system registered extensions!`. Run the command
given to add lintcheck to your system's IDLE extension config file.
3) Again run command `typecheck`. This time, you should see the following
output: `Config should be good!`.
4) Open IDLE, go to `Options` -> `Configure IDLE` -> `Extensions`.
If everything went well, alongside `ZzDummy` there should be and
option called `typecheck`. This is where you can configure how
lintcheck works.

### Information on options
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

If you add the `--show-column-numbers` flag to `daemon_flags`, when using the
"Type Check File" command, it will add a helpful little `^` sign
in a new line below the location of the mypy message that provided a column
number, as long as that comment wouldn't break your file's indentation too much.

If you add the `--show-error-codes` flag to `daemon_flags`, when using the
"Type Check File" command, when it puts mypy's comments in your code, it will
tell you what type of error that comment is. For example, it would change the
error comment
```python
# types: error: Incompatible types in assignment (expression has type "str", variable has type "int")
```
to
```python
# types: assignment error: Incompatible types in assignment (expression has type "str", variable has type "int")
```

`search_wrap` toggles weather searching for next type comment will wrap
around or not.
