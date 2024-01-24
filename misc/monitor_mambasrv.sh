#!/bin/bash

## Look for duplicated deadman files for the same port/web service:
## remove them and kill their processes
cd /tmp/
for deadman in `ls deadman* | sort | uniq --check-chars=13 -c | grep  -v '1 ' | awk '{print $2}' `
do
    # echo $deadman # only keep this copy 
    find -type f -name "${deadman::13}*" ! -name $deadman -exec bash -c ' kill `echo {} | cut -d. -f4` ; rm {} ' \;  2>/dev/null
done


# change to correct directory
cd /data/string_v12/mamba

# check for deadman files
for f in /tmp/*
do
	filename=$(echo $f | cut -d'.' -f1)
	if [[ $filename == "/tmp/deadman" ]]
	then
	my_port=$(echo $f | cut -d'.' -f2)
	#echo "check for port "$my_port	

	my_pid=$(echo $f | cut -d'.' -f3)
	#echo "found deadman file for "$my_pid

	uname=$(stat -c '%U' $f)
	#echo "deadman file created by "$uname

	found_process=$(ps aux | grep $my_pid | grep -v grep)
	#echo $found_process

	if [[ $found_process == "" ]]
	then
		#echo "Server not running. Start server."
		start_command=`cat $f`
		rm $f
		#eval "$start_command" &
		eval "sudo -u $uname $start_command &"
	else
		status=$(curl -s -w '%{http_code}' -o /dev/null --connect-timeout 5 --max-time 10 http://localhost:$my_port/GetStatus)
		if [[ ! $status == "200" ]]
		then
			#echo "Server restart needed."
			start_command=`cat $f`
			kill -9 $my_pid
			rm $f
			sleep 10
			eval "sudo -u $uname $start_command &"
			#eval "$start_command" &
		#else
			#echo "All fine."
		fi
	fi
	fi
done

