#!/bin/csh -f
foreach i (compartments tissues diseases organisms)
./mambasrv config/$i.ini >& log/$i.log &
end
