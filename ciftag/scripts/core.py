from sqlalchemy import text

from ciftag.integrations.database import DBManager

dbm = DBManager()


def select_sql(sql, args=None, target='all'):
    """ sql 기반 조회 """
    with dbm.create_connection() as conn:
        cur = conn.execute(text(sql), args)

        if target == "all":
            result = cur.fetchall()
        else:
            result = cur.fetchone()

    return result


def save_sql(sql, args=None, returning=False):
    """ sql 기반 insert/update """
    with dbm.create_connection() as conn:
        cur = conn.execute(text(sql), args)

    row_count = cur.rowcount
    effect_row = 0

    if returning and "RETURNING" in sql.upper():
        effect_row = cur.fetchone()  # tuple로 열 내용 반환

        if returning == "id":
            effect_row = effect_row[0]

    return row_count, effect_row

