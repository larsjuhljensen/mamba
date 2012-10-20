#!/bin/csh -f
foreach i (compartments diseases tissues yeastphenotypes stringdocuments)
./mambasrv config/$i.ini >& log/$i.log &
end
