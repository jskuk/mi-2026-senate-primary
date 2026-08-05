#!/bin/zsh
# Stream ACS 5-year 2023 tables, keeping only Michigan block groups (1500000US26)
# and tracts (1400000US26). Avoids storing ~90MB per national table.
cd /private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad
mkdir -p acs
B="https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData"

for t in b15003 b01001 b19025 b11001 b05002 b04006 b19013 b25003; do
  out="acs/${t}_mi.psv"
  if [[ -s "$out" ]]; then echo "skip $t"; continue; fi
  curl -sL "$B/acsdt5y2023-${t}.dat" \
    | grep -E '^(GEO_ID|1500000US26|1400000US26)' > "$out"
  echo "$t -> $(wc -l < "$out") rows"
done
echo DONE
