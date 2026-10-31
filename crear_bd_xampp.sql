CREATE DATABASE IF NOT EXISTS CrisFerreterias
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'crisferreterias_app'@'127.0.0.1'
  IDENTIFIED BY 'crissteel_xampp_2026';
ALTER USER 'crisferreterias_app'@'127.0.0.1'
  IDENTIFIED BY 'crissteel_xampp_2026';

CREATE USER IF NOT EXISTS 'crisferreterias_app'@'localhost'
  IDENTIFIED BY 'crissteel_xampp_2026';
ALTER USER 'crisferreterias_app'@'localhost'
  IDENTIFIED BY 'crissteel_xampp_2026';

GRANT ALL PRIVILEGES ON CrisFerreterias.*
  TO 'crisferreterias_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON CrisFerreterias.*
  TO 'crisferreterias_app'@'localhost';
GRANT ALL PRIVILEGES ON CrisFerreterias_test.*
  TO 'crisferreterias_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON CrisFerreterias_test.*
  TO 'crisferreterias_app'@'localhost';
GRANT CREATE, DROP ON *.*
  TO 'crisferreterias_app'@'127.0.0.1';
GRANT CREATE, DROP ON *.*
  TO 'crisferreterias_app'@'localhost';

FLUSH PRIVILEGES;
