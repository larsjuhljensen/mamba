#!/bin/csh -f
foreach i (compartments diseases tissues yeastphenotypes)
./mambasrv config/$i.ini >& log/$i.log &
end
