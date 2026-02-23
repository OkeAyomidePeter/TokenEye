#!/bin/bash
# scripts/check_progress.sh
# 
# Commands to check TokenEye production stats on EC2.

DB_NAME="tokenscout"
DB_USER="ayomide"

echo "============================================================"
echo " 🔍 TOKENEYE PRODUCTION PROGRESS"
echo "============================================================"

echo -e "\n--- OVERALL STATS ---"
psql -U $DB_USER -d $DB_NAME -h localhost -c "
SELECT 
    (SELECT COUNT(*) FROM tokens_discovered) as total_tokens,
    (SELECT COUNT(*) FROM token_history) as total_snapshots,
    (SELECT COUNT(*) FROM tokens_discovered WHERE rugged = true) as rugged_count;
"

echo -e "\n--- SNAPSHOT DISTRIBUTION ---"
psql -U $DB_USER -d $DB_NAME -h localhost -c "
SELECT check_type, COUNT(*) 
FROM token_history 
GROUP BY check_type 
ORDER BY 
    CASE check_type 
        WHEN '1h' THEN 1 WHEN '3h' THEN 2 WHEN '6h' THEN 3 
        WHEN '1d' THEN 4 WHEN '1w' THEN 5 WHEN '1m' THEN 6 
        WHEN '3m' THEN 7 
    END;
"

echo -e "\n--- COMPLETE DATASETS (Ready for AI) ---"
psql -U $DB_USER -d $DB_NAME -h localhost -c "
SELECT COUNT(*) as complete_7_of_7
FROM (
    SELECT token_address 
    FROM token_history 
    GROUP BY token_address 
    HAVING COUNT(DISTINCT check_type) = 7
) as sub;
"

echo -e "\n--- HIGH POTENTIAL TOKENS ---"
psql -U $DB_USER -d $DB_NAME -h localhost -c "SELECT COUNT(*) FROM tokens_discovered WHERE classification = 'high potential';"

echo "============================================================"
