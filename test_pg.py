import asyncio
import asyncpg
import urllib.parse

async def test_connection():
    user = "postgres"
    password = "Phuc2005@"  # nếu có ký tự đặc biệt như @, #, ! cần URL-encode
    host = "localhost"
    port = 5432
    database = "postgres"

    # URL encode password
    password_encoded = urllib.parse.quote_plus(password)

    DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    print("Trying to connect to:", DATABASE_URL)

    try:
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port
        )
        print("Connection successful!")
        await conn.close()
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    asyncio.run(test_connection())
