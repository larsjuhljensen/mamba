#!/bin/csh -f
foreach i (chemicals compartments tissues diseases organisms stringdocuments stitchdocuments docrank hoods seqenv)
./mambasrv config/$i.ini >& log/$i.log &
end
./mambasrv miRPD/miRPD.ini >& miRPD/miRPD.log &
