#!/bin/bash

NAME=""
SWAP=""
USER_ID=""
USER=""
MEMORY_TYPE=""
MEMORY=""
PID=""
VRAC=""

# Manage the script argument
if [ $# -ne 0 ]
then
        while [ -n "$1" ] ; do
                case "$1" in
                        --m*|-m)
                                MEMORY_TYPE=$2
                                shift
                                ;;
                        *)
                                echo "A memory type must be specified with the -m"
                                echo "Ex : swap.sh -m VmSize" => RAM
                                echo "Ex : swap.sh -m SWAP" => SWAP
                                exit 1
                                ;;
                        esac
                        shift
        done
else
        echo "A memory type must be specified with the -m"
        echo "Ex : swap.sh -m VmSize" => RAM
        echo "Ex : swap.sh -m VmSwap" => SWAP
        exit 1
fi

# Display the memory usage
while read file
do
        if [ $MEMORY_TYPE == "VmSize" ]
        then
                if [ -e $file ]
                then
                        VRAC=`awk '/Uid|VmSize|Name/{printf $2 " " $3}END{ print " " }' $file`
                        NAME=`echo $VRAC | cut -d " " -f1`
                        PID=`echo $file | cut -d "/" -f3 2> /dev/null`
                        USER_ID=`echo $VRAC | cut -d " " -f2`
                        USER=`getent passwd $USER_ID | cut -d":" -f1`
                        MEMORY=`echo $VRAC | cut -d " " -f3`
                        echo "${NAME}|${PID}|${USER}|${MEMORY}"
                fi
        elif [ $MEMORY_TYPE == "VmSwap" ]
        then
                if [ -e $file ]
                then
                        VRAC=`awk '/Uid|VmSwap|Name/{printf $2 " " $3}END{ print " " }' $file`
                        NAME=`echo $VRAC | cut -d " " -f1`
                        PID=`echo $file | cut -d "/" -f3 2> /dev/null`
                        USER_ID=`echo $VRAC | cut -d " " -f2`
                        USER=`getent passwd $USER_ID | cut -d":" -f1`
                        MEMORY=`echo $VRAC | cut -d " " -f3`
                        echo "${NAME}|${PID}|${USER}|${MEMORY}"
                fi
        fi
done < <(ls /proc/*/status) | sort -t"|" -k4 -n -r | head -15

exit 0
