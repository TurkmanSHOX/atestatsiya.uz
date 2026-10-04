-- =====================================================================
-- ATTESTATSIYA.UZ 2.0 - MARIADB / MYSQL DATABASE SCHEMA
-- O'zbekiston maktab o'qituvchilari uchun attestatsiyaga tayyorlov platformasi
-- Standart: utf8mb4 / InnoDB (HeidiSQL mosligi)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `attestatsiya_uz` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `attestatsiya_uz`;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Users jadvali (Faqat 2 ta rol: ADMIN va FOYDALANUVCHI)
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `role` ENUM('ADMIN', 'FOYDALANUVCHI') NOT NULL DEFAULT 'FOYDALANUVCHI',
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `phone` VARCHAR(30) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `first_name` VARCHAR(80) NOT NULL,
    `last_name` VARCHAR(80) NOT NULL,
    `middle_name` VARCHAR(80) NULL,
    `birth_date` DATE NULL,
    `gender` ENUM('ERKAK', 'AYOL') NULL,
    `region` VARCHAR(100) NULL,
    `organization` VARCHAR(255) NULL,
    `position` VARCHAR(150) NULL,
    `specialty` VARCHAR(150) NULL,
    `experience_years` INT DEFAULT 0,
    `avatar_path` VARCHAR(255) NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `is_verified` BOOLEAN DEFAULT FALSE,
    `two_factor_enabled` BOOLEAN DEFAULT FALSE,
    `two_factor_secret` VARCHAR(64) NULL,
    `last_login_at` DATETIME NULL,
    `last_login_ip` VARCHAR(45) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role_status` (`role`, `is_active`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Fanlar (Subjects)
DROP TABLE IF EXISTS `subjects`;
CREATE TABLE `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(150) NOT NULL UNIQUE,
    `slug` VARCHAR(150) NOT NULL UNIQUE,
    `code` VARCHAR(50) NULL,
    `description` TEXT NULL,
    `image_path` VARCHAR(255) NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `order_num` INT DEFAULT 0,
    `category` VARCHAR(100) DEFAULT 'Maktab fani',
    `academic_year` VARCHAR(20) DEFAULT '2024-2025',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_subjects_active_order` (`is_active`, `order_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Bo'limlar (Subject Sections)
DROP TABLE IF EXISTS `subject_sections`;
CREATE TABLE `subject_sections` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_id` INT NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `order_num` INT DEFAULT 0,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE,
    INDEX `idx_sections_subject` (`subject_id`, `order_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Mavzular (Topics)
DROP TABLE IF EXISTS `topics`;
CREATE TABLE `topics` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_id` INT NOT NULL,
    `section_id` INT NULL,
    `name` VARCHAR(150) NOT NULL,
    `code` VARCHAR(50) NULL,
    `order_num` INT DEFAULT 0,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`section_id`) REFERENCES `subject_sections`(`id`) ON DELETE SET NULL,
    INDEX `idx_topics_subject_section` (`subject_id`, `section_id`, `order_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Kichik mavzular (Subtopics)
DROP TABLE IF EXISTS `subtopics`;
CREATE TABLE `subtopics` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `topic_id` INT NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `order_num` INT DEFAULT 0,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`) ON DELETE CASCADE,
    INDEX `idx_subtopics_topic` (`topic_id`, `order_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Savollar (Questions)
DROP TABLE IF EXISTS `questions`;
CREATE TABLE `questions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_id` INT NOT NULL,
    `section_id` INT NULL,
    `topic_id` INT NOT NULL,
    `subtopic_id` INT NULL,
    `question_type` VARCHAR(30) NOT NULL DEFAULT 'SINGLE_CHOICE',
    `text` TEXT NOT NULL,
    `explanation` TEXT NULL,
    `difficulty` ENUM('EASY', 'MEDIUM', 'HARD') DEFAULT 'MEDIUM',
    `points` DECIMAL(5,2) DEFAULT 1.00,
    `source` VARCHAR(255) NULL,
    `academic_year` VARCHAR(20) DEFAULT '2024-2025',
    `tags` VARCHAR(255) NULL,
    `status` ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE',
    `is_approved` BOOLEAN DEFAULT TRUE,
    `version` INT DEFAULT 1,
    `hash` VARCHAR(64) NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`),
    FOREIGN KEY (`section_id`) REFERENCES `subject_sections`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`),
    FOREIGN KEY (`subtopic_id`) REFERENCES `subtopics`(`id`) ON DELETE SET NULL,
    INDEX `idx_questions_subject_topic` (`subject_id`, `topic_id`, `status`),
    INDEX `idx_questions_hash` (`hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Savol variantlari (Question Options)
DROP TABLE IF EXISTS `question_options`;
CREATE TABLE `question_options` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `question_id` INT NOT NULL,
    `key` VARCHAR(10) NOT NULL,
    `text` TEXT NULL,
    `is_correct` BOOLEAN DEFAULT FALSE,
    `order_num` INT DEFAULT 0,
    `explanation` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE,
    INDEX `idx_options_question` (`question_id`, `is_correct`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7.1. Javob varianti medialari (Question Option Media)
DROP TABLE IF EXISTS `question_option_media`;
CREATE TABLE `question_option_media` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `option_id` INT NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_url` VARCHAR(255) NULL,
    `original_name` VARCHAR(255) NULL,
    `mime_type` VARCHAR(100) NULL,
    `file_size` INT NULL,
    `media_type` VARCHAR(20) DEFAULT 'IMAGE',
    `sort_order` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`option_id`) REFERENCES `question_options`(`id`) ON DELETE CASCADE,
    INDEX `idx_option_media_option` (`option_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Savol versiyalari (Question Versions)
DROP TABLE IF EXISTS `question_versions`;
CREATE TABLE `question_versions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `question_id` INT NOT NULL,
    `version_number` INT NOT NULL,
    `text` TEXT NOT NULL,
    `explanation` TEXT NULL,
    `difficulty` VARCHAR(20) NULL,
    `options_json` JSON NULL,
    `created_by_id` INT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`created_by_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Savol medialari (Question Media)
DROP TABLE IF EXISTS `question_media`;
CREATE TABLE `question_media` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `question_id` INT NOT NULL,
    `media_type` VARCHAR(20) NOT NULL DEFAULT 'IMAGE',
    `file_path` VARCHAR(255) NOT NULL,
    `file_url` VARCHAR(255) NULL,
    `original_name` VARCHAR(255) NULL,
    `mime_type` VARCHAR(100) NULL,
    `file_size` INT NULL,
    `caption` VARCHAR(255) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Paketlar (Packages)
DROP TABLE IF EXISTS `packages`;
CREATE TABLE `packages` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(150) NOT NULL,
    `slug` VARCHAR(150) NOT NULL UNIQUE,
    `description` TEXT NULL,
    `price` DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    `duration_days` INT NOT NULL DEFAULT 30,
    `test_limit` INT NULL,
    `is_all_subjects` BOOLEAN DEFAULT TRUE,
    `is_active` BOOLEAN DEFAULT TRUE,
    `features` JSON NULL,
    `order_num` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Paket fanlari (Package Subjects)
DROP TABLE IF EXISTS `package_subjects`;
CREATE TABLE `package_subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `package_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    FOREIGN KEY (`package_id`) REFERENCES `packages`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Buyurtmalar (Orders)
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_number` VARCHAR(50) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `package_id` INT NOT NULL,
    `amount` DECIMAL(12,2) NOT NULL,
    `status` ENUM('PENDING', 'PAID', 'CANCELLED', 'EXPIRED') DEFAULT 'PENDING',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`package_id`) REFERENCES `packages`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. To'lovlar (Payments)
DROP TABLE IF EXISTS `payments`;
CREATE TABLE `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `amount` DECIMAL(12,2) NOT NULL,
    `currency` VARCHAR(10) DEFAULT 'UZS',
    `payment_method` VARCHAR(30) DEFAULT 'CLICK',
    `click_trans_id` VARCHAR(100) NULL UNIQUE,
    `click_paydoc_id` VARCHAR(100) NULL,
    `sign_time` VARCHAR(50) NULL,
    `status` ENUM('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'REFUNDED', 'EXPIRED') DEFAULT 'PENDING',
    `error_code` INT DEFAULT 0,
    `error_note` VARCHAR(255) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. To'lov hodisalari (Payment Events)
DROP TABLE IF EXISTS `payment_events`;
CREATE TABLE `payment_events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `payment_id` INT NULL,
    `event_type` VARCHAR(50) NOT NULL,
    `payload` JSON NULL,
    `status` VARCHAR(30) DEFAULT 'SUCCESS',
    `ip_address` VARCHAR(45) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`payment_id`) REFERENCES `payments`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. Foydalanuvchi huquqlari (Entitlements)
DROP TABLE IF EXISTS `entitlements`;
CREATE TABLE `entitlements` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `package_id` INT NOT NULL,
    `order_id` INT NULL,
    `subject_id` INT NULL,
    `starts_at` DATETIME NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `tests_remaining` INT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`package_id`) REFERENCES `packages`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE,
    INDEX `idx_entitlements_user_active` (`user_id`, `is_active`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. Testlar (Tests)
DROP TABLE IF EXISTS `tests`;
CREATE TABLE `tests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL,
    `test_type` ENUM('MAVZU', 'FAN', 'ARALASH', 'SIMULYATSIYA', 'XATOLAR', 'ZAIF_MAVZULAR', 'TASODIFIY') DEFAULT 'FAN',
    `subject_id` INT NULL,
    `topic_id` INT NULL,
    `duration_minutes` INT NOT NULL DEFAULT 60,
    `passing_score` DECIMAL(5,2) NOT NULL DEFAULT 60.00,
    `total_questions` INT DEFAULT 30,
    `shuffle_questions` BOOLEAN DEFAULT TRUE,
    `shuffle_options` BOOLEAN DEFAULT TRUE,
    `is_free` BOOLEAN DEFAULT FALSE,
    `status` ENUM('ACTIVE', 'DRAFT') DEFAULT 'ACTIVE',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. Test savollari (Test Questions)
DROP TABLE IF EXISTS `test_questions`;
CREATE TABLE `test_questions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `test_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `order_num` INT DEFAULT 0,
    FOREIGN KEY (`test_id`) REFERENCES `tests`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. Test Blueprint
DROP TABLE IF EXISTS `test_blueprints`;
CREATE TABLE `test_blueprints` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `test_id` INT NOT NULL UNIQUE,
    `total_questions` INT NOT NULL DEFAULT 40,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`test_id`) REFERENCES `tests`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 19. Test Blueprint qoidalari
DROP TABLE IF EXISTS `test_blueprint_rules`;
CREATE TABLE `test_blueprint_rules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `blueprint_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `topic_id` INT NULL,
    `difficulty` VARCHAR(20) DEFAULT 'ANY',
    `questions_count` INT NOT NULL DEFAULT 10,
    FOREIGN KEY (`blueprint_id`) REFERENCES `test_blueprints`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`),
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 20. Test sessiyalari (Test Sessions)
DROP TABLE IF EXISTS `test_sessions`;
CREATE TABLE `test_sessions` (
    `id` VARCHAR(36) PRIMARY KEY,
    `user_id` INT NOT NULL,
    `test_id` INT NOT NULL,
    `started_at` DATETIME NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `finished_at` DATETIME NULL,
    `status` ENUM('IN_PROGRESS', 'SUBMITTED', 'EXPIRED', 'TERMINATED') DEFAULT 'IN_PROGRESS',
    `ip_address` VARCHAR(45) NULL,
    `user_agent` TEXT NULL,
    `last_heartbeat_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`test_id`) REFERENCES `tests`(`id`) ON DELETE CASCADE,
    INDEX `idx_sessions_status_expires` (`status`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 21. Test javoblari (Test Answers)
DROP TABLE IF EXISTS `test_answers`;
CREATE TABLE `test_answers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(36) NOT NULL,
    `question_id` INT NOT NULL,
    `selected_option_ids` JSON NULL,
    `text_answer` TEXT NULL,
    `is_flagged` BOOLEAN DEFAULT FALSE,
    `is_correct` BOOLEAN NULL,
    `awarded_points` DECIMAL(5,2) DEFAULT 0.00,
    `answered_at` DATETIME NULL,
    `time_spent_seconds` INT DEFAULT 0,
    FOREIGN KEY (`session_id`) REFERENCES `test_sessions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE,
    INDEX `idx_answers_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 22. Natijalar (Results)
DROP TABLE IF EXISTS `results`;
CREATE TABLE `results` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(36) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `test_id` INT NOT NULL,
    `total_questions` INT NOT NULL,
    `correct_answers` INT NOT NULL,
    `incorrect_answers` INT NOT NULL,
    `unanswered` INT NOT NULL,
    `score` DECIMAL(6,2) NOT NULL,
    `percentage` DECIMAL(5,2) NOT NULL,
    `is_passed` BOOLEAN NOT NULL,
    `completion_time_seconds` INT NOT NULL,
    `ai_recommendation` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`session_id`) REFERENCES `test_sessions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`test_id`) REFERENCES `tests`(`id`) ON DELETE CASCADE,
    INDEX `idx_results_user` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 23. Natijalar tafsiloti (Result Details)
DROP TABLE IF EXISTS `result_details`;
CREATE TABLE `result_details` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `result_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `topic_id` INT NULL,
    `total_topic_questions` INT NOT NULL,
    `correct_topic_questions` INT NOT NULL,
    `topic_percentage` DECIMAL(5,2) NOT NULL,
    FOREIGN KEY (`result_id`) REFERENCES `results`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`),
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 24. Foydalanuvchi savol statistikasi (User Question Stats - Xatolarim)
DROP TABLE IF EXISTS `user_question_stats`;
CREATE TABLE `user_question_stats` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `attempts_count` INT DEFAULT 1,
    `correct_count` INT DEFAULT 0,
    `incorrect_count` INT DEFAULT 0,
    `is_last_correct` BOOLEAN DEFAULT FALSE,
    `last_attempt_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_question` (`user_id`, `question_id`),
    INDEX `idx_user_qstats_mistakes` (`user_id`, `is_last_correct`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 25. Foydalanuvchi mavzu statistikasi (User Topic Stats - Zaif mavzular)
DROP TABLE IF EXISTS `user_topic_stats`;
CREATE TABLE `user_topic_stats` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `topic_id` INT NOT NULL,
    `total_answered` INT DEFAULT 0,
    `correct_answered` INT DEFAULT 0,
    `accuracy_percentage` DECIMAL(5,2) DEFAULT 0.00,
    `last_updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_topic` (`user_id`, `topic_id`),
    INDEX `idx_user_topic_weak` (`user_id`, `accuracy_percentage`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 26. Saqlangan savollar (Bookmarks)
DROP TABLE IF EXISTS `bookmarks`;
CREATE TABLE `bookmarks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `notes` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_bookmark` (`user_id`, `question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 27. Telegram admin foydalanuvchilar
DROP TABLE IF EXISTS `telegram_users`;
CREATE TABLE `telegram_users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `telegram_chat_id` VARCHAR(64) NOT NULL UNIQUE,
    `username` VARCHAR(100) NULL,
    `full_name` VARCHAR(150) NULL,
    `role` VARCHAR(20) DEFAULT 'ADMIN',
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 28. Bildirishnomalar (Notifications)
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `message` TEXT NOT NULL,
    `link` VARCHAR(255) NULL,
    `is_read` BOOLEAN DEFAULT FALSE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 29. Audit jurnali (Audit Logs)
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `action` VARCHAR(50) NOT NULL,
    `entity` VARCHAR(50) NOT NULL,
    `entity_id` VARCHAR(50) NULL,
    `old_values` JSON NULL,
    `new_values` JSON NULL,
    `ip_address` VARCHAR(45) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 30. Tizim sozlamalari (Settings)
DROP TABLE IF EXISTS `settings`;
CREATE TABLE `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `key_name` VARCHAR(100) NOT NULL UNIQUE,
    `value_text` TEXT NULL,
    `group_name` VARCHAR(50) DEFAULT 'GENERAL',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
