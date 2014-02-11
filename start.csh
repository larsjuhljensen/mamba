#!/bin/csh -f
foreach i (chemicals compartments diseases environments tissues organisms yeastphenotypes stringdocuments stitchdocuments docrank hoods)
./mambasrv config/$i.ini >& log/$i.log &
end
./mambasrv miRPD/miRPD.ini >& miRPD/miRPD.log &
