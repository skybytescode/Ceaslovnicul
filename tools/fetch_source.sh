#!/bin/sh
# Re-download the source pages and parse them into source/blocks/.
set -e
cd "$(dirname "$0")/.."
mkdir -p source/raw source/blocks
B=https://sites.google.com/site/ortodox007
for pair in \
  "ceaslovul ceaslovul" \
  "rugaciuni ceaslovul/rug%C4%83ciuni-din-ceaslov" \
  "tipicul5 tipicul/tipicul-seria-a-cincea" \
  "sinaxar ceaslovul/sinaxar" \
  "calendar calendar-cre%C8%99tin-ortodox" \
  "psaltirea psaltirea" \
  "canon-treime ceaslovul/canonul-sfintei-treimi" \
  "canoane-md ceaslovul/canoanele-maicii-domnului" \
  "octoih octoihul-mare" \
  "triodul triodul"; do
  set -- $pair
  curl -sSL -A "Mozilla/5.0 Ceaslovnicul" -o "source/raw/$1.html" "$B/$2"
  python3 -I tools/html2blocks.py "source/raw/$1.html" "source/blocks/$1.json"
  sleep 1
done
