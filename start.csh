#!/bin/csh -f
foreach i (chemicals compartments diseases tissues organisms yeastphenotypes stringdocuments docrank hoods)
./mambasrv config/$i.ini >& log/$i.log &
end
