#!/usr/bin/env bash
# Documents an attempted read of the sealed reference optimum from the
# unprivileged verifier stage. Never executed by harbor; see cheat/README.md
# for the actual measured result.
su -s /bin/bash runner -c "cat /tests/sealed/reference/optimum.json"
