#!/bin/bash
# Initialize test database using environment variables
# This creates the test database and applies the same schema as the main database

echo "Setting up test database: $TEST_MYSQL_DATABASE"

# Create test database and grant permissions using environment variables
mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS \`$TEST_MYSQL_DATABASE\`;
GRANT ALL PRIVILEGES ON \`$TEST_MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
FLUSH PRIVILEGES;
EOF

echo "Applying schema to test database..."

# Apply the schema.sql to the test database
mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$TEST_MYSQL_DATABASE" < /docker-entrypoint-initdb.d/schema.sql

echo "Test database setup completed successfully." 