#!/bin/bash
docker run --env-file=env.list --name ibeam -p 5000:5000 -v ./inputs_alt:/srv/inputs voyz/ibeam
