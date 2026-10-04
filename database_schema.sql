-- =====================================================================
-- ATTESTATSIYA.UZ - MARIADB / MYSQL DATABASE SCHEMA
-- Boshqaruv vositasi: HeidiSQL / MariaDB Client
-- Standart: utf8mb4 / InnoDB
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

-- 2. User Documents
DROP TABLE IF EXISTS `user_documents`;
CREATE TABLE `user_documents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `doc_type` ENUM('PASSPORT', 'DIPLOM', 'MEHNAT_DAFTARCHASI', 'SERTIFIKAT', 'BOSHQA') NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_size` INT NOT NULL,
    `mime_type` VARCHAR(80) NOT NULL,
    `verification_status` ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
    `verified_at` DATETIME NULL,
    `admin_notes` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Attestations
DROP TABLE IF EXISTS `attestations`;
CREATE TABLE `attestations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL,
    `slug` VARCHAR(255) NOT NULL UNIQUE,
    `short_description` VARCHAR(500) NOT NULL,
    `full_description` LONGTEXT NOT NULL,
    `field_name` VARCHAR(150) NOT NULL,
    `price` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    `currency` VARCHAR(10) NOT NULL DEFAULT 'UZS',
    `questions_count` INT NOT NULL DEFAULT 40,
    `duration_minutes` INT NOT NULL DEFAULT 60,
    `passing_score` DECIMAL(5,2) NOT NULL DEFAULT 60.00,
    `max_score` DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    `max_attempts` INT NOT NULL DEFAULT 1,
    `retake_delay_days` INT DEFAULT 30,
    `show_result_immediately` BOOLEAN DEFAULT TRUE,
    `show_answers_after_exam` BOOLEAN DEFAULT FALSE,
    `issue_certificate` BOOLEAN DEFAULT TRUE,
    `certificate_validity_months` INT DEFAULT 36,
    `starts_at` DATETIME NULL,
    `ends_at` DATETIME NULL,
    `status` ENUM('DRAFT', 'ACTIVE', 'PAUSED', 'FINISHED', 'ARCHIVED') DEFAULT 'DRAFT',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_att_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Attestation Registrations
DROP TABLE IF EXISTS `attestation_registrations`;
CREATE TABLE `attestation_registrations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `registration_number` VARCHAR(32) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `attestation_id` INT NOT NULL,
    `step` ENUM('REGISTERED', 'DOCUMENTS', 'PAYMENT', 'ADMIN_REVIEW', 'APPROVED', 'EXAM_READY', 'COMPLETED', 'REJECTED') DEFAULT 'REGISTERED',
    `admin_comment` TEXT NULL,
    `reviewed_by` INT NULL,
    `reviewed_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`attestation_id`) REFERENCES `attestations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`reviewed_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_reg_step` (`step`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Payments & Receipts
DROP TABLE IF EXISTS `payments`;
CREATE TABLE `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `registration_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `amount` DECIMAL(12,2) NOT NULL,
    `currency` VARCHAR(10) DEFAULT 'UZS',
    `payment_method` ENUM('CARD_MANUAL', 'BANK_TRANSFER', 'CLICK', 'PAYME', 'UZCARD_HUMO') DEFAULT 'CARD_MANUAL',
    `transaction_id` VARCHAR(120) NULL UNIQUE,
    `status` ENUM('PENDING', 'PAID', 'REJECTED', 'REFUNDED', 'EXPIRED') DEFAULT 'PENDING',
    `rejection_reason` TEXT NULL,
    `confirmed_by` INT NULL,
    `confirmed_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`registration_id`) REFERENCES `attestation_registrations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`confirmed_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_pay_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `payment_receipts`;
CREATE TABLE `payment_receipts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `payment_id` INT NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_size` INT NULL,
    `mime_type` VARCHAR(80) NOT NULL,
    `uploaded_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`payment_id`) REFERENCES `payments`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Subjects, Topics, Questions
DROP TABLE IF EXISTS `subjects`;
CREATE TABLE `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(150) NOT NULL UNIQUE,
    `code` VARCHAR(50) NULL,
    `description` TEXT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `topics`;
CREATE TABLE `topics` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_id` INT NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `code` VARCHAR(50) NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `questions`;
CREATE TABLE `questions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_id` INT NOT NULL,
    `topic_id` INT NOT NULL,
    `question_type` ENUM('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'TRUE_FALSE', 'MATCHING', 'ORDERING', 'IMAGE_BASED', 'TABLE_BASED', 'FORMULA_BASED', 'AUDIO_BASED', 'VIDEO_BASED', 'FILL_BLANK') NOT NULL,
    `text` LONGTEXT NOT NULL,
    `explanation` TEXT NULL,
    `difficulty` ENUM('EASY', 'MEDIUM', 'HARD') DEFAULT 'MEDIUM',
    `points` DECIMAL(5,2) DEFAULT 1.00,
    `status` ENUM('DRAFT', 'ACTIVE', 'ARCHIVED') DEFAULT 'ACTIVE',
    `hash` VARCHAR(64) NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`),
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`),
    INDEX `idx_q_hash` (`hash`),
    INDEX `idx_q_criteria` (`subject_id`, `topic_id`, `difficulty`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `question_options`;
CREATE TABLE `question_options` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `question_id` INT NOT NULL,
    `option_key` VARCHAR(10) NULL,
    `text` TEXT NOT NULL,
    `is_correct` BOOLEAN DEFAULT FALSE NOT NULL,
    `order_index` INT DEFAULT 0,
    `match_key` VARCHAR(100) NULL,
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Tests and Blueprints
DROP TABLE IF EXISTS `tests`;
CREATE TABLE `tests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attestation_id` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `duration_minutes` INT NOT NULL DEFAULT 60,
    `passing_score` DECIMAL(5,2) NOT NULL DEFAULT 60.00,
    `shuffle_questions` BOOLEAN DEFAULT TRUE,
    `shuffle_options` BOOLEAN DEFAULT TRUE,
    `proctoring_enabled` BOOLEAN DEFAULT TRUE,
    `status` ENUM('DRAFT', 'ACTIVE', 'ARCHIVED') DEFAULT 'DRAFT',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`attestation_id`) REFERENCES `attestations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `test_blueprints`;
CREATE TABLE `test_blueprints` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `test_id` INT NOT NULL UNIQUE,
    `total_questions` INT NOT NULL DEFAULT 40,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`test_id`) REFERENCES `tests`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `test_blueprint_rules`;
CREATE TABLE `test_blueprint_rules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `blueprint_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `topic_id` INT NULL,
    `difficulty` ENUM('ANY', 'EASY', 'MEDIUM', 'HARD') DEFAULT 'ANY',
    `questions_count` INT NOT NULL DEFAULT 10,
    FOREIGN KEY (`blueprint_id`) REFERENCES `test_blueprints`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`),
    FOREIGN KEY (`topic_id`) REFERENCES `topics`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Exam Sessions and Answers
DROP TABLE IF EXISTS `test_sessions`;
CREATE TABLE `test_sessions` (
    `id` VARCHAR(36) PRIMARY KEY,
    `user_id` INT NOT NULL,
    `test_id` INT NOT NULL,
    `registration_id` INT NOT NULL,
    `started_at` DATETIME NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `finished_at` DATETIME NULL,
    `status` ENUM('IN_PROGRESS', 'SUBMITTED', 'EXPIRED', 'TERMINATED') DEFAULT 'IN_PROGRESS',
    `ip_address` VARCHAR(45) NOT NULL,
    `user_agent` TEXT NOT NULL,
    `device_fingerprint` VARCHAR(128) NULL,
    `last_heartbeat_at` DATETIME NOT NULL,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`test_id`) REFERENCES `tests`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`registration_id`) REFERENCES `attestation_registrations`(`id`) ON DELETE CASCADE,
    INDEX `idx_sess_status_expiry` (`status`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    FOREIGN KEY (`question_id`) REFERENCES `questions`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `proctoring_events`;
CREATE TABLE `proctoring_events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(36) NOT NULL,
    `user_id` INT NOT NULL,
    `event_type` VARCHAR(50) NOT NULL,
    `severity` ENUM('LOW', 'MEDIUM', 'HIGH') DEFAULT 'LOW',
    `details` JSON NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`session_id`) REFERENCES `test_sessions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Results and Certificates
DROP TABLE IF EXISTS `results`;
CREATE TABLE `results` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(36) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `attestation_id` INT NOT NULL,
    `total_questions` INT NOT NULL,
    `correct_answers` INT NOT NULL,
    `incorrect_answers` INT NOT NULL,
    `unanswered` INT NOT NULL,
    `score` DECIMAL(6,2) NOT NULL,
    `percentage` DECIMAL(5,2) NOT NULL,
    `is_passed` BOOLEAN NOT NULL,
    `completion_time_seconds` INT NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`session_id`) REFERENCES `test_sessions`(`id`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`attestation_id`) REFERENCES `attestations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `result_details`;
CREATE TABLE `result_details` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `result_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `topic_id` INT NULL,
    `total_topic_questions` INT NOT NULL,
    `correct_topic_questions` INT NOT NULL,
    `topic_percentage` DECIMAL(5,2) NOT NULL,
    FOREIGN KEY (`result_id`) REFERENCES `results`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `certificates`;
CREATE TABLE `certificates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `certificate_number` VARCHAR(64) NOT NULL UNIQUE,
    `verification_uuid` VARCHAR(64) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `attestation_id` INT NOT NULL,
    `result_id` INT NOT NULL UNIQUE,
    `issue_date` DATE NOT NULL,
    `valid_until` DATE NOT NULL,
    `status` ENUM('ACTIVE', 'EXPIRED', 'REVOKED', 'CANCELLED') DEFAULT 'ACTIVE',
    `pdf_path` VARCHAR(255) NULL,
    `qr_code_path` VARCHAR(255) NULL,
    `revocation_reason` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`attestation_id`) REFERENCES `attestations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`result_id`) REFERENCES `results`(`id`) ON DELETE CASCADE,
    INDEX `idx_cert_verif` (`verification_uuid`, `certificate_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `certificate_verifications`;
CREATE TABLE `certificate_verifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `certificate_id` INT NOT NULL,
    `verified_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `ip_address` VARCHAR(45) NULL,
    `user_agent` TEXT NULL,
    FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Audit, Settings, Notifications
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
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_audit_action_time` (`action`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `settings`;
CREATE TABLE `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `key_name` VARCHAR(100) NOT NULL UNIQUE,
    `value_text` LONGTEXT NULL,
    `group_name` VARCHAR(50) DEFAULT 'GENERAL',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

SET FOREIGN_KEY_CHECKS = 1;
