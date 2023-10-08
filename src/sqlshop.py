import sqlite3

class SQLTable:
    def __init__(self, filename: str):
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        # Создать таблицу, если она еще не существует
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS mytable (
                user_id INTEGER PRIMARY KEY,
                date DATE,
                items TEXT
            )
        '''
        self.cursor.execute(create_table_query)
        self.conn.commit()

    def insert_data(self, user_id: int, date: str, items: list):
        insert_query = "INSERT INTO mytable (user_id, date, items) VALUES (?, ?, ?)"
        self.cursor.execute(insert_query, (user_id, date, ",".join(items)))
        self.conn.commit()

    def update_data(self, user_id: int, date: str, new_items: list):
        update_query = "UPDATE mytable SET items = ? WHERE user_id = ? AND date = ?"
        self.cursor.execute(update_query, (",".join(new_items), user_id, date))
        self.conn.commit()

    def delete_data(self, user_id, date):
        delete_query = "DELETE FROM mytable WHERE user_id = ? AND date = ?"
        self.cursor.execute(delete_query, (user_id, date))
        self.conn.commit()

    def get_data(self, user_id, date):
        select_query = "SELECT * FROM mytable WHERE user_id = ? AND date = ?"
        self.cursor.execute(select_query, (user_id, date))
        result = self.cursor.fetchone()
        if result:
            user_id, date, items = result
            items_list = items.split(',')
            return user_id, date, items_list

    def close(self):
        self.conn.close()

########################

shoptable = SQLTable(r"databases/shoptable.sql")

