# IdleTypeCheck
Python IDLE extension to preform mypy analysis on an open file

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
