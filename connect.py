import os

import mysql.connector
from mysql.connector import Error


def connect_to_mysql():
	try:
		connection = mysql.connector.connect(
			host=os.getenv("MYSQL_HOST", "127.0.0.1"),
			port=int(os.getenv("MYSQL_PORT", "3306")),
			user=os.getenv("MYSQL_USER", "root"),
			password=os.getenv("MYSQL_PASSWORD", ""),
			database=os.getenv("MYSQL_DATABASE", "three_tb_db"),
			connection_timeout=5,
		)

		if connection.is_connected():
			return connection
	except Error as error:
		print(f"MySQL connection error: {error}")

	return None
