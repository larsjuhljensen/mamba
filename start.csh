#!/bin/csh -f
foreach i (compartments diseases tissues organisms yeastphenotypes stringdocuments docrank)
./mambasrv config/$i.ini >& log/$i.log &
end
