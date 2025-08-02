from google.cloud.sql.connector import Connector
import pg8000

connector = Connector()

def getconn():
    return connector.connect(
        "odoo-ai-transformer:europe-west9:odoo-ai-transformer-db",
        "pg8000",
        user="postgres",
        password="Cluso11235813!",
        db="app_data"
    )

conn = getconn()
cursor = conn.cursor()
cursor.execute("SELECT 1;")
print(cursor.fetchone())
conn.close()