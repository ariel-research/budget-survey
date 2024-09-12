CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  external_id INT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE survey_responses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  survey_name VARCHAR(255) NOT NULL,
  optimal_allocation JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE comparison_pairs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  survey_response_id INT NOT NULL,
  pair_number INT NOT NULL,
  option_1 JSON NOT NULL,
  option_2 JSON NOT NULL,
  user_choice INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (survey_response_id) REFERENCES survey_responses(id)
);
