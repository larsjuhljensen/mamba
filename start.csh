#!/bin/csh -f
foreach i (compartments diseases tissues yeastphenotypes)
./mambasrv $i.ini >& $i.log &
end
