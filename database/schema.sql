CREATE TABLE users (
  id INT NOT NULL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surveys (
  id INT NOT NULL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  subjects JSON NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE survey_responses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  survey_id INT NOT NULL,
  optimal_allocation JSON NOT NULL,
  completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (survey_id) REFERENCES surveys(id)
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
