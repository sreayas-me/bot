from utils.db import db

def setup_database():
    """Initialize database tables"""
    try:
        # Economy table with guild support
        db.cursor.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER,
                guild_id INTEGER DEFAULT 0,
                wallet INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Guild stats table
        db.cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_stats (
                guild_id INTEGER,
                stat_type TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, stat_type)
            )
        """)

        db.conn.commit()
        print("Database tables initialized successfully")
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

if __name__ == "__main__":
    setup_database()
