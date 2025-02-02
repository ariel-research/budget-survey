CREATE TABLE users (
  id VARCHAR(128) NOT NULL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surveys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  subjects JSON NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  pair_generation_config JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_external_id (external_id),
  UNIQUE KEY uq_external_id (external_id)
);

CREATE TABLE survey_responses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(128) NOT NULL,
  survey_id INT NOT NULL,
  optimal_allocation JSON NOT NULL,
  user_comment TEXT,
  completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

CREATE TABLE comparison_pairs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  survey_response_id INT NOT NULL,
  pair_number INT NOT NULL,
  option_1 JSON NOT NULL,
  option_2 JSON NOT NULL,
  user_choice INT NOT NULL,      -- User choice after swap adjustment
  option1_strategy VARCHAR(100),     -- Strategy used to generate option 1
  option2_strategy VARCHAR(100),     -- Strategy used to generate option 2
  raw_user_choice INT NULL,      -- Original user choice before swap adjustment
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (survey_response_id) REFERENCES survey_responses(id)
);
