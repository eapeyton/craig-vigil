import sqlite3

def insert_listing(**values):
    conn = sqlite3.connect('apartment.db')
    cursor = conn.cursor()
    count = len(values)
    params = tuple(values.values())
    stmnt = "INSERT INTO listings (" + ','.join(values.keys()) + ") VALUES (" + ','.join('?'*count) + ")"
    print(stmnt)
    print(params)
    cursor.execute(stmnt,params)
    conn.commit()
    conn.close()


insert_listing(id='19230489',title='hel')
