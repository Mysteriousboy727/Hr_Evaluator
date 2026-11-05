import sqlite3
c = sqlite3.connect("hr.db")
for r in c.execute("select id, name, email, phone, role from users where role = 'hr'"):
    print(r)
