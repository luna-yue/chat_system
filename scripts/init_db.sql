-- Chat System 数据库初始化脚本
-- 自动创建所有表

CREATE DATABASE IF NOT EXISTS TestDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE TestDB;

-- 用户表
CREATE TABLE IF NOT EXISTS `User` (
  `id` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `user_id` varchar(64) NOT NULL,
  `nickname` varchar(64) NULL,
  `description` TEXT NULL,
  `password` varchar(64) NULL,
  `phone` varchar(64) NULL,
  `avatar_id` varchar(64) NULL
) ENGINE=InnoDB;

CREATE UNIQUE INDEX `user_id_i` ON `User` (`user_id`);
CREATE UNIQUE INDEX `nickname_i` ON `User` (`nickname`);
CREATE UNIQUE INDEX `phone_i` ON `User` (`phone`);

-- 好友关系表
CREATE TABLE IF NOT EXISTS `relation` (
  `id` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `user_id` varchar(64) NOT NULL,
  `peer_id` varchar(64) NOT NULL
) ENGINE=InnoDB;

CREATE INDEX `relation_user_id_i` ON `relation` (`user_id`);

-- 好友申请表
CREATE TABLE IF NOT EXISTS `friend_apply` (
  `id` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `event_id` varchar(64) NOT NULL,
  `user_id` varchar(64) NOT NULL,
  `peer_id` varchar(64) NOT NULL
) ENGINE=InnoDB;

CREATE UNIQUE INDEX `friend_apply_event_id_i` ON `friend_apply` (`event_id`);
CREATE INDEX `friend_apply_user_id_i` ON `friend_apply` (`user_id`);

-- 聊天会话表
CREATE TABLE IF NOT EXISTS `chat_session` (
  `id` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `chat_session_id` varchar(64) NOT NULL,
  `chat_session_name` varchar(128) NULL,
  `chat_session_type` TINYINT UNSIGNED NOT NULL
) ENGINE=InnoDB;

CREATE UNIQUE INDEX `chat_session_id_i` ON `chat_session` (`chat_session_id`);

-- 聊天会话成员表
CREATE TABLE IF NOT EXISTS `chat_session_member` (
  `id` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `session_id` varchar(64) NOT NULL,
  `user_id` varchar(64) NOT NULL
) ENGINE=InnoDB;

CREATE INDEX `chat_session_member_session_id_i` ON `chat_session_member` (`session_id`);

-- 消息表
CREATE TABLE IF NOT EXISTS `Message` (
  `id` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `message_id` varchar(64) NOT NULL,
  `session_id` varchar(64) NOT NULL,
  `user_id` varchar(64) NOT NULL,
  `message_type` TINYINT UNSIGNED NOT NULL,
  `create_time` TIMESTAMP NULL,
  `content` TEXT NULL,
  `file_id` varchar(64) NULL,
  `file_name` varchar(128) NULL,
  `file_size` INT UNSIGNED NULL
) ENGINE=InnoDB;

CREATE UNIQUE INDEX `message_id_i` ON `Message` (`message_id`);
CREATE INDEX `message_session_id_i` ON `Message` (`session_id`);
