#!/usr/bin/env bash
rootdir=`dirname $0`
if ! [ -d "$rootdir/venv" ]; then
   python3 -m venv venv
   source venv/bin/activate
   PIP_REQUIRE_VIRTUALENV=true pip install -r requirements.txt
fi
