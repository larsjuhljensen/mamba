#!/bin/csh -f
foreach i (stringdocuments stitchdocuments)
./mambasrv config/$i.ini >& log/$i.log &
end
