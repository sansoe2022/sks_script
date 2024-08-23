#!/bin/bash

password=$((4455))
echo "Enter login key number"
read x

if [ $x -eq $password ]
then
echo "Success login"
sleep 2
echo "Welcome to sks script"
elif [ $x -ne $password ]
then
echo "Key is incorrect"
echo "Exiting..."
sleep 2
exit


fi
