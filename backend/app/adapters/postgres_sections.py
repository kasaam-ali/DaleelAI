"""Read parent sections from Postgres. A missing driver or table returns no rows."""


class PostgresSections:
    def __init__(self, database_url: str, connect=None) -> None:
        self.database_url = database_url
        self._connect = connect

    def __call__(self, parent_ids: list[str]) -> dict[str, str]:
        if not parent_ids or not self.database_url:
            return {}
        connect = self._connect or self._open
        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT parent_id, text FROM sections WHERE parent_id = ANY(%s)",
                        (list(parent_ids),),
                    )
                    return {row[0]: row[1] for row in cur.fetchall()}
        except Exception:
            return {}

    def _open(self):
        import psycopg

        return psycopg.connect(self.database_url, connect_timeout=5)
