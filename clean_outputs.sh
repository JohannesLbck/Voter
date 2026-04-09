#!/bin/bash
# Keep only the most recent batch of XML files in Outputs/

DIR="$(dirname "$0")/Outputs"

# Find the latest timestamp from filenames (last _TIMESTAMP.xml segment)
LATEST=$(ls -t "$DIR"/*.xml 2>/dev/null | head -1 | grep -oP '_\K[0-9]+(?=\.xml$)')

if [ -z "$LATEST" ]; then
    echo "No XML files found in $DIR"
    exit 0
fi

echo "Keeping files with timestamp: $LATEST"

for f in "$DIR"/*.xml; do
    if [[ "$f" != *_${LATEST}.xml ]]; then
        echo "Removing: $(basename "$f")"
        rm "$f"
    fi
done

echo "Done."
