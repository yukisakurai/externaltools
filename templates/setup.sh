# This generated script will work in either bash or zsh.

# deterine path to this script
# http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
EXTERNALTOOLS_SETUP="${BASH_SOURCE[0]:-$0}"

EXTERNALTOOLS_DIR="$( dirname "$EXTERNALTOOLS_SETUP" )"
while [ -h "$EXTERNALTOOLS_SETUP" ]
do 
  EXTERNALTOOLS_SETUP="$(readlink "$EXTERNALTOOLS_SETUP")"
  [[ $EXTERNALTOOLS_SETUP != /* ]] && EXTERNALTOOLS_SETUP="$EXTERNALTOOLS_DIR/$EXTERNALTOOLS_SETUP"
  EXTERNALTOOLS_SETUP="$( cd -P "$( dirname "$EXTERNALTOOLS_SETUP"  )" && pwd )"
done
EXTERNALTOOLS_DIR="$( cd -P "$( dirname "$EXTERNALTOOLS_SETUP" )" && pwd )"

echo "sourcing ${EXTERNALTOOLS_SETUP}..."
export PYTHONPATH=${EXTERNALTOOLS_DIR}${PYTHONPATH:+:$PYTHONPATH}
