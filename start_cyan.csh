#!/bin/csh -f
foreach i (organisms compartments tissues diseases api tagger cyclebase hoods stringdocuments stitchdocuments)
./mambasrv config/$i.ini >& log/$i.log &
end
./mambasrv miRPD/miRPD.ini >& miRPD/miRPD.log &
./mambasrv miRPC/miRPC.ini >& miRPC/miRPC.log &
