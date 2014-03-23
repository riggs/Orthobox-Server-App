Documentation
=============

Hopefully this project will import into PyCharm smoothly.

You may need to manually create a virtualenv (via Python Interpreter preferences in PyCharm) called 'orthobox'. If it
doesn't automatically install the requirements, run pip install -r requirements.txt inside the virtualenv to install
the required packages.

Due to a recent release of XCode, compiling packages from source via pip (as required for lxml) breaks in OS X. This is
one particular work-around: ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future pip install <blah>

Installing lxml, itself, on OS X requires an additional flag of STATIC_DEPS=true, thus:
STATIC_DEPS=true ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future pip install lxml