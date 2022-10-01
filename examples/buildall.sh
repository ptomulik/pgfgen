#!/usr/bin/env bash

set -e

mkdir -p build/examples/tex

for SOURCE in examples/svg/*.tex.jinja; do
  TARGET=`echo $SOURCE | sed -e 's:examples/svg/\(.\+\)\.jinja$:build/examples/tex/\1:'`
  pgfgen -o "$TARGET" "$SOURCE"
  pdflatex -interaction=nonstopmode -output-directory=build/examples/tex "$TARGET"
  pdflatex -interaction=nonstopmode -output-directory=build/examples/tex "$TARGET"
done
