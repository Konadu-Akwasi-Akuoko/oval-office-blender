#!/usr/bin/env bash
# Wait for the detached Blender render to finish, then encode to mp4.
#
# Launch with nohup so it outlives any tool timeout:
#   nohup ./scripts/finish_render.sh > renders/finish.log 2>&1 &
#
# A backgrounded Bash tool call cannot do this: those cap at 10 minutes and the
# render takes about 3.5 hours, so the waiter gets killed while the render
# carries on. nohup detaches it from the session entirely, the same way the
# render itself is detached.

set -uo pipefail
cd "$(dirname "$0")/.."

echo "waiting for render, $(ls renders/frames/*.png 2>/dev/null | wc -l | tr -d ' ') frames so far"

while pgrep -f "Blender -b oval_office" >/dev/null; do
    sleep 60
done

count=$(ls renders/frames/*.png 2>/dev/null | wc -l | tr -d ' ')
echo "render finished with $count frames"

if [ "$count" -lt 600 ]; then
    echo "WARNING: expected 600 frames, got $count. The loop will not close."
fi

./scripts/encode.sh
echo "done"
