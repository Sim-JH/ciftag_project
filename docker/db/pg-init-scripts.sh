et -e
set -u

# postgres compose 시, multiple db 자동 생성
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
	echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
	for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
		create_user_and_database $db
	done
	echo "Multiple databases created"
	for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
		set_disk_info $db
	done
fi

# docker 내/외부 디스크 용량 조회
function set_disk_info() {
  local database=$1
	echo "set database info '$database'"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$database" <<-EOSQL
    CREATE OR REPLACE FUNCTION sys_df() RETURNS SETOF text[] AS
    \$\$
    BEGIN
        CREATE TEMP TABLE IF NOT EXISTS tmp_sys_df (content text) ON COMMIT DROP;
        COPY tmp_sys_df FROM PROGRAM 'df $PGDATA | tail -n +2';
        RETURN QUERY SELECT regexp_split_to_array(content, '\s+') FROM tmp_sys_df;
    END;
    \$\$
    LANGUAGE plpgsql
EOSQL
}

