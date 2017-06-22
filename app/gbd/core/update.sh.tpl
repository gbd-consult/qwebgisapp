#!/bin/bash

APPID=${appid}

DIR=$(dirname "$0")
cd $DIR
if [ $# -eq 0 ]; then
    rm -f $APPID.zip
    curl -s -o $APPID.zip http://dev.gbd-consult.de/packages/$APPID
fi
rm -fr app
unzip -q $APPID.zip
if [ ! -f config.ini ]; then
    cp app/config.ini config.ini
fi

# cat "$DIR/app/apt.lst" | xargs apt-get install -y
# pip install -q -r "$DIR/app/pip.lst"

echo 'Update installed.'
echo 'To activate the new configuration, you need to run:'
echo "   sudo python $DIR/app/gbd/bin/setup.py $DIR/config.ini"
