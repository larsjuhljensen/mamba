#!/bin/csh -f
foreach i (tissues yeastphenotypes stringdocuments stitchdocuments docrank hoods)
./mambasrv config/$i.ini >& log/$i.log &
end
./mambasrv miRPD/miRPD.ini >& miRPD/miRPD.log &
./mambasrv miRPD/miRPC.ini >& miRPD/miRPC.log &
