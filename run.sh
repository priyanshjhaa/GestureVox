#!/bin/bash
# GestureVox launcher. Works from any folder, and sets itself up on first run.
#
#   ./run.sh                 start GestureVox (with practice mode)
#   ./run.sh quick           start without practice mode
#   ./run.sh study P1        user study session for participant P1 (log: logs/P1_...)
#   ./run.sh access          large text + left-handed mode
#   ./run.sh v1              the original v1 prototype (for comparison)
#   ./run.sh test            run all tests
#   ./run.sh help            show this help
#
# Extra options are passed through, e.g.  ./run.sh quick --no-sound --blackout

set -e
cd "$(dirname "$0")"
PY=.venv/bin/python

setup() {
    if [ ! -x "$PY" ]; then
        echo "First run: installing GestureVox (about a minute)..."
        python3 -m venv .venv
        .venv/bin/pip install -q --upgrade pip
        .venv/bin/pip install -q -r requirements.txt
        echo "Done."
    fi
}

usage() {
    sed -n '4,12p' "$0" | sed 's/^# \{0,1\}//'
}

command="${1:-start}"
[ $# -gt 0 ] && shift

case "$command" in
    start)  setup; exec "$PY" v2_gesturevox.py "$@" ;;
    quick)  setup; exec "$PY" v2_gesturevox.py --skip-practice "$@" ;;
    access) setup; exec "$PY" v2_gesturevox.py --large-text --left-handed "$@" ;;
    v1)     setup; exec "$PY" v1_basic.py "$@" ;;
    study)
        if [ -z "$1" ]; then
            echo "Usage: ./run.sh study P1"
            exit 1
        fi
        participant="$1"; shift
        setup; exec "$PY" v2_gesturevox.py --participant "$participant" "$@" ;;
    test)
        setup
        "$PY" test_v2.py && "$PY" test_features.py && "$PY" test_swipe.py
        echo "All tests passed." ;;
    help|-h|--help) usage ;;
    *)
        # e.g. ./run.sh --no-sound: treat as options for the normal start
        if [[ "$command" == -* ]]; then
            setup; exec "$PY" v2_gesturevox.py "$command" "$@"
        fi
        echo "Unknown command: $command"; echo; usage; exit 1 ;;
esac
