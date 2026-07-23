import os
import json
import uuid
from datetime import datetime
from decimal import Decimal
from psycopg2.extras import RealDictCursor

# Import the normalized database connection helper from src
from src.database.db import get_db_connection

class DatabaseEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle PostgreSQL-specific types like UUID, Datetime, and Decimal.
    """
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            # Convert decimal to float or int for standard JSON compatibility
            return float(obj) if '.' in str(obj) else int(obj)
        return super().default(obj)

def export_resumes():
    output_filename = "exported_resumes.json"
    print("Connecting to the database...")
    
    conn = None
    try:
        conn = get_db_connection()
        # Using RealDictCursor so that results are formatted as dictionaries (column_name: value)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("Executing query: SELECT * FROM resumes;")
            cur.execute("SELECT * FROM resumes;")
            rows = cur.fetchall()
            
            print(f"Successfully retrieved {len(rows)} resume record(s).")
            
            # Serialize to JSON using the custom encoder
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, cls=DatabaseEncoder)
                
            print(f"Data successfully exported to: {os.path.abspath(output_filename)}")
            
    except Exception as e:
        print(f"An error occurred during database export: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    export_resumes()
