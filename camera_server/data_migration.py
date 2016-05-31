#!/usr/bin/env python3

import sqlite3

conn = sqlite3.connect('Parking.db')

c = conn.cursor()
# Create table
c.execute('''CREATE TABLE traffic
             (lot_id INTEGER , plate text, datetime timestamp)''')

conn.commit()