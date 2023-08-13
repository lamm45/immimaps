#!/bin/bash

thisdir="$(dirname -- "$(realpath -- "${BASH_SOURCE[0]}")")"
cd "$thisdir"

wget --no-clobber --input-file="urls.txt"
sha256sum --check "checksums.sha256"
