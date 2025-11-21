import psycopg2

# Connect to the database
conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='Dev#31padia', database='postgres')
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
tables = cursor.fetchall()
print("Tables:", tables)

# Check media_files table structure
cursor.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'media_files' ORDER BY ordinal_position")
columns = cursor.fetchall()
print("Media_files columns:", columns)

# Check project 136
cursor.execute("SELECT id, name, social_medias FROM projects WHERE id = 136")
project = cursor.fetchall()
print("Project 136:", project)

# Check credentials for project 136
cursor.execute("SELECT * FROM social_media_credentials WHERE project_id = 136")
credentials = cursor.fetchall()
print("Credentials for 136:", credentials)

# Check all credentials
cursor.execute("SELECT project_id, platform, fb_page_id, fb_page_access_token FROM social_media_credentials ORDER BY project_id DESC LIMIT 10")
all_credentials = cursor.fetchall()
print("All credentials:", all_credentials)

# Check all projects
cursor.execute("SELECT id, name, social_medias FROM projects ORDER BY id DESC LIMIT 5")
projects = cursor.fetchall()
print("Recent projects:", projects)

conn.close()

