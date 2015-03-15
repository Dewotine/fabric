#!/bin/bash

NAME=""
SWAP=""
USER_ID=""
USER=""
MEMORY_TYPE=""
MEMORY=""
PID=""
VRAC=""
LINE=15

# Manage the script argument
if [ $# -ne 0 ]
then
        while [ -n "$1" ] ; do
                case "$1" in
                        --memory|-m)
                                MEMORY_TYPE=$2
                                shift
                                ;;
			--line|-l)
				LINE=$2
				shift
				;;				
                        *)
                                echo "A memory type must be specified with the -m"
                                echo "Ex : swap.sh -m VmSize" => RAM
                                echo "Ex : swap.sh -m SWAP" => FULL
                                exit 1
                                ;;
                        esac
                        shift
        done
else
        echo "A memory type must be specified with the -m"
        echo "Ex : swap.sh -m VmSize" => RAM
        echo "Ex : swap.sh -m VmSwap" => FULL
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
                        #echo "${NAME}|${PID}|${USER}|${MEMORY}"
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
                        #echo "${NAME}|${PID}|${USER}|${MEMORY}"
                fi
        fi
        printf "%-15s | %-5s | %-10s | %s"  ${NAME} ${PID} ${USER} ${MEMORY}
        echo ""
done < <(ls /proc/*/status) | sort -t"|" -k4 -n -r | head -$LINE

exit 0
