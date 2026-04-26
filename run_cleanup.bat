@echo off
chcp 65001 > nul
set PGPASSWORD=Ibra3898@
psql -U postgres -d agriasset -f clean.sql > psql_output.log 2>&1
echo DONE >> psql_output.log
