#!/bin/sh
pipfile2req > requirements.txt
python3 setup.py sdist bdist_wheel
#python3 -m pip install --user --upgrade twine
python3 -m twine upload dist/*