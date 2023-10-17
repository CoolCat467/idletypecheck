# IdleTypeCheck
Python IDLE extension to perform mypy analysis on an open file

<!-- BADGIE TIME -->

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![code style: black](https://img.shields.io/badge/code_style-black-000000.svg)](https://github.com/psf/black)

<!-- END BADGIE TIME -->

## Installation
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
See `mypy --help` for more information.
