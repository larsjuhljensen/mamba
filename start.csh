#!/bin/csh -f
foreach i (chemicals compartments diseases environments tissues organisms yeastphenotypes stringdocuments docrank hoods miRPD)
./mambasrv config/$i.ini >& log/$i.log &
end
