#!/bin/bash

pylint probables/

echo 'pylint status code:' $?

exit 0

# Will exit with status of last command.
