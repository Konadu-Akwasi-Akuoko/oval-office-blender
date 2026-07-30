#!/usr/bin/env bash
# Encode the rendered PNG sequence to mp4.
#
# Run from the project root, after the render has finished:
#   ./scripts/encode.sh
#
# Frames are rendered as a PNG sequence rather than straight to video so that a
# crash or a sleeping laptop partway through a 3.5-hour job does not lose
# everything. This is the second half of that.

set -euo pipefail

FRAMES_DIR="renders/frames"
OUT="renders/oval_office_360.mp4"
FPS=30
EXPECTED=600

count=$(find "$FRAMES_DIR" -name 'oo_*.png' | wc -l | tr -d ' ')
if [ "$count" -eq 0 ]; then
    echo "No frames in $FRAMES_DIR. Has the render run?" >&2
    exit 1
fi
if [ "$count" -lt "$EXPECTED" ]; then
    echo "WARNING: only $count of $EXPECTED frames present." >&2
    echo "Encoding anyway, but the loop will not close." >&2
fi

# yuv420p and the even-dimension filter, because some players reject odd sizes
# and anything but 4:2:0. -crf 17 is visually lossless for this material.
ffmpeg -y \
    -framerate "$FPS" \
    -i "$FRAMES_DIR/oo_%04d.png" \
    -c:v libx264 \
    -preset slow \
    -crf 17 \
    -pix_fmt yuv420p \
    -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    -movflags +faststart \
    "$OUT"

echo
echo "Wrote $OUT"
echo "Frames: $count at ${FPS} fps = $(echo "scale=1; $count / $FPS" | bc) seconds"
echo
echo "The loop is seamless: the 360-degree keyframe sits on frame 601 while the"
echo "timeline ends at 600, so no frame is duplicated at the join."
