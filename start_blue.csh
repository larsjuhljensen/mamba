#!/bin/csh -f
foreach i (compartments tissues diseases organisms tagger)
./mambasrv config/$i.ini >& log/$i.log &
end
