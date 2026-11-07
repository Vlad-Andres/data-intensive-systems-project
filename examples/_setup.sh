# Sourced by the example scripts: run from the project root with Java 21 (Spark does not start on newer Java).
cd "$(dirname "${BASH_SOURCE[0]}")/.."
JAVA_21_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
[ -d "$JAVA_21_HOME" ] && export JAVA_HOME="$JAVA_21_HOME"

GRAPH=${GRAPH:-data/DatabaseX_7.txt}
QLOG=${QLOG:-data/QLog7_2.txt}
KEEP=${KEEP:-0.02}

run() { echo "+ uv run main.py $*"; uv run main.py "$@"; }
