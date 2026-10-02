import psycopg2

DB_URL = "postgresql://neondb_owner:npg_CNe6bvKfQ2pn@ep-morning-art-b3gc6nk9-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute('ALTER TABLE "user" ALTER COLUMN avatar_val TYPE TEXT;')
    cur.execute('ALTER TABLE product_images ALTER COLUMN filename TYPE TEXT;')
    cur.execute('ALTER TABLE user_calendar ALTER COLUMN source TYPE TEXT;')
    
    conn.commit()
    print("Columns altered to TEXT successfully.")
except Exception as e:
    print(e)
    conn.rollback()
finally:
    if 'cur' in locals(): cur.close()
    if 'conn' in locals(): conn.close()
