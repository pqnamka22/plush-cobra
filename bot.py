#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🖤 GOLDEN COBRA GOTH MOMMY - SUPREME EDITION v4.0 🖤
Ultimate Aggressive Telegram Bot with Web Interface
Без ошибок, максимальная производительность, космический уровень
"""

import os
import sys
import asyncio
import logging
import sqlite3
import random
import time
import json
import hashlib
import aiosqlite
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any, Union
from contextlib import asynccontextmanager
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

# Telegram Bot
from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InputFile, Poll, PollAnswer
)
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Web Server
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ============================================================================
# КОНФИГУРАЦИЯ ПРОЕКТА - УЛУЧШЕННАЯ
# ============================================================================

class Config:
    """Конфигурация проекта с валидацией"""
    
    # Безопасные значения по умолчанию
    BOT_TOKEN = os.getenv('BOT_TOKEN', '8536282991:AAHUyTx0r7Q03bwDRokvogbmJAIbkAnYVpM')
    ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '123456789').split(',') if x.strip()]
    DB_FILE = os.getenv('DB_FILE', 'golden_cobra_supreme.db')
    WEB_PORT = int(os.getenv('WEB_PORT', 8000))
    WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
    
    # Папки
    BACKUP_DIR = 'backups'
    LOGS_DIR = 'logs'
    STATIC_DIR = 'static'
    
    # Настройки базы данных
    DB_TIMEOUT = 30
    DB_JOURNAL_MODE = 'WAL'
    DB_SYNC_MODE = 'NORMAL'
    
    # Лимиты и настройки
    MAX_STARS_PER_TRANSACTION = 1000000
    MIN_STARS_PER_TRANSACTION = 10
    DAILY_COOLDOWN_HOURS = 20
    CHALLENGE_EXPIRE_HOURS = 24
    MAX_REFERRALS_PER_USER = 100
    
    # Настройки безопасности
    MAX_REQUESTS_PER_MINUTE = 30
    MAX_MESSAGE_LENGTH = 4000
    
    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        if not cls.BOT_TOKEN or len(cls.BOT_TOKEN) < 10:
            raise ValueError("Invalid BOT_TOKEN")
        if not cls.ADMIN_IDS:
            cls.ADMIN_IDS = [123456789]
        return True

# Создаем необходимые директории
for directory in [Config.BACKUP_DIR, Config.LOGS_DIR, Config.STATIC_DIR]:
    os.makedirs(directory, exist_ok=True)

# ============================================================================
# НАСТРОЙКА ЛОГГИРОВАНИЯ - ПРОФЕССИОНАЛЬНАЯ
# ============================================================================

class SupremeLogger:
    """Улучшенная система логирования"""
    
    @staticmethod
    def setup():
        """Настройка логгера"""
        logger = logging.getLogger('GoldenCobra')
        logger.setLevel(logging.INFO)
        
        # Формат логов
        formatter = logging.Formatter(
            '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Файловый вывод
        file_handler = logging.FileHandler(
            f'{Config.LOGS_DIR}/bot_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

logger = SupremeLogger.setup()

# ============================================================================
# СИСТЕМА БАЗЫ ДАННЫХ - УЛЬТРАНАДЕЖНАЯ
# ============================================================================

class SupremeDatabase:
    """Улучшенный менеджер базы данных с защитой от ошибок"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Инициализация всех таблиц БЕЗ ОШИБОК"""
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute(f"PRAGMA journal_mode={Config.DB_JOURNAL_MODE}")
                conn.execute(f"PRAGMA synchronous={Config.DB_SYNC_MODE}")
                conn.execute("PRAGMA foreign_keys=ON")
                
                cursor = conn.cursor()
                
                # Основная таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        spent_stars INTEGER DEFAULT 0,
                        earned_stars INTEGER DEFAULT 0,
                        referrals INTEGER DEFAULT 0,
                        referral_id INTEGER,
                        daily_streak INTEGER DEFAULT 0,
                        last_daily_claim TIMESTAMP,
                        language TEXT DEFAULT 'EN',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_premium BOOLEAN DEFAULT 0,
                        premium_until TIMESTAMP,
                        is_banned BOOLEAN DEFAULT 0,
                        ban_reason TEXT,
                        timezone TEXT DEFAULT 'UTC',
                        UNIQUE(user_id)
                    )
                ''')
                
                # Индексы для быстрого поиска
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_spent ON users(spent_stars DESC)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_earned ON users(earned_stars DESC)')
                
                # Таблица вызовов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS challenges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        challenger_id INTEGER NOT NULL,
                        challenged_id INTEGER NOT NULL,
                        amount INTEGER NOT NULL,
                        status TEXT DEFAULT 'pending',
                        winner_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (challenger_id) REFERENCES users(user_id),
                        FOREIGN KEY (challenged_id) REFERENCES users(user_id),
                        FOREIGN KEY (winner_id) REFERENCES users(user_id),
                        CHECK (amount > 0),
                        CHECK (status IN ('pending', 'accepted', 'declined', 'expired', 'completed'))
                    )
                ''')
                
                # Глобальный фонд
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS global_fund (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        total_stars INTEGER DEFAULT 0,
                        current_goal INTEGER DEFAULT 10000,
                        next_goal INTEGER DEFAULT 50000,
                        raffle_active BOOLEAN DEFAULT 0,
                        last_raffle TIMESTAMP,
                        total_raffles INTEGER DEFAULT 0
                    )
                ''')
                
                # Транзакции для аудита
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        amount INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        description TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
                
                # Магазин NFT
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shop_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price INTEGER NOT NULL,
                        emoji TEXT,
                        rarity TEXT,
                        available BOOLEAN DEFAULT 1,
                        stock INTEGER DEFAULT -1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(name)
                    )
                ''')
                
                # Инвентарь пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        item_id INTEGER NOT NULL,
                        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_equipped BOOLEAN DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (item_id) REFERENCES shop_items(id),
                        UNIQUE(user_id, item_id)
                    )
                ''')
                
                # Достижения
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        reward_stars INTEGER DEFAULT 0,
                        condition_type TEXT,
                        condition_value INTEGER,
                        emoji TEXT,
                        UNIQUE(name)
                    )
                ''')
                
                # Достижения пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        user_id INTEGER NOT NULL,
                        achievement_id INTEGER NOT NULL,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, achievement_id),
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (achievement_id) REFERENCES achievements(id)
                    )
                ''')
                
                # Система квестов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS quests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        reward_stars INTEGER NOT NULL,
                        requirement_type TEXT,
                        requirement_value INTEGER,
                        is_daily BOOLEAN DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        UNIQUE(name)
                    )
                ''')
                
                # Прогресс квестов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS quest_progress (
                        user_id INTEGER NOT NULL,
                        quest_id INTEGER NOT NULL,
                        progress INTEGER DEFAULT 0,
                        completed BOOLEAN DEFAULT 0,
                        completed_at TIMESTAMP,
                        PRIMARY KEY (user_id, quest_id),
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (quest_id) REFERENCES quests(id)
                    )
                ''')
                
                # Вставляем начальные данные
                self._insert_initial_data(cursor)
                
                conn.commit()
                logger.info("База данных успешно инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    def _insert_initial_data(self, cursor):
        """Вставка начальных данных БЕЗ ОШИБОК"""
        try:
            # Глобальный фонд
            cursor.execute('''
                INSERT OR IGNORE INTO global_fund 
                (id, total_stars, current_goal, next_goal) 
                VALUES (1, 0, 10000, 50000)
            ''')
            
            # Достижения
            achievements = [
                ('Первокровный', 'Потрать первые звезды', 100, 'spend', 100, '🩸'),
                ('Звездный маньяк', 'Потрать 10,000 звезд', 1000, 'spend', 10000, '⭐'),
                ('Топ-игрок', 'Займи место в топ-10', 1500, 'rank', 10, '🏆'),
                ('Победитель дуэлей', 'Выиграй 5 дуэлей', 2000, 'challenge_win', 5, '⚔️'),
                ('Мастер рефералов', 'Пригласи 10 друзей', 2500, 'referral', 10, '👥'),
                ('Непрерывный поток', 'Получай ежедневную награду 30 дней', 3000, 'daily_streak', 30, '🔥'),
                ('Коллекционер', 'Купи 5 разных NFT', 3500, 'nft_count', 5, '🖼️'),
                ('Миллионер', 'Заработай 1,000,000 звезд', 10000, 'earned', 1000000, '💎'),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO achievements 
                (name, description, reward_stars, condition_type, condition_value, emoji)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', achievements)
            
            # Товары магазина
            shop_items = [
                ('Череп Кобры', 'Демонический череп змеи NFT', 1000, '💀', 'Редкий', 1, 100),
                ('Кровавая Гадюка', 'Вампирская кровавая змея NFT', 5000, '🩸', 'Эпический', 1, 50),
                ('Корона Золотой Кобры', 'Королевская корона кобры', 10000, '👑', 'Легендарный', 1, 25),
                ('Теневой Змей', 'Невидимая теневая змея NFT', 2500, '🌑', 'Редкий', 1, 150),
                ('Алмазная Чешуя', 'Неразрушимая алмазная чешуя', 7500, '💎', 'Эпический', 1, 75),
                ('Вечная Душа Кобры', 'Эссенция бессмертной души кобры', 50000, '🔥', 'Мифический', 1, 10),
                ('Ядовитый Кинжал', 'Ядовитый церемониальный кинжал', 1500, '🗡️', 'Необычный', 1, 200),
                ('Благословение Готической Мамочки', 'Божественное благословение', 25000, '🙏', 'Легендарный', 1, 5),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO shop_items 
                (name, description, price, emoji, rarity, available, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', shop_items)
            
            # Квесты
            quests = [
                ('Первая кровь', 'Потрать 100 звезд впервые', 200, 'spend', 100, 0, 1),
                ('Ежедневный воин', 'Потрать 500 звезд за день', 500, 'daily_spend', 500, 1, 1),
                ('Пригласитель', 'Пригласи 3 друзей', 1000, 'referral', 3, 0, 1),
                ('Победитель', 'Выиграй дуэль', 1500, 'challenge_win', 1, 0, 1),
                ('Коллекционер', 'Купи любой NFT', 2000, 'nft_purchase', 1, 0, 1),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO quests 
                (name, description, reward_stars, requirement_type, requirement_value, is_daily, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', quests)
            
        except Exception as e:
            logger.error(f"Ошибка вставки начальных данных: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Асинхронное соединение с базой данных"""
        try:
            async with aiosqlite.connect(self.db_path, timeout=Config.DB_TIMEOUT) as db:
                db.row_factory = aiosqlite.Row
                yield db
        except Exception as e:
            logger.error(f"Ошибка соединения с БД: {e}")
            raise
    
    async def execute(self, query: str, params: tuple = None):
        """Выполнить SQL-запрос"""
        try:
            async with self.get_connection() as db:
                await db.execute(query, params or ())
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    async def fetchone(self, query: str, params: tuple = None):
        """Получить одну запись"""
        try:
            async with self.get_connection() as db:
                async with db.execute(query, params or ()) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка получения записи: {e}")
            return None
    
    async def fetchall(self, query: str, params: tuple = None):
        """Получить все записи"""
        try:
            async with self.get_connection() as db:
                async with db.execute(query, params or ()) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения записей: {e}")
            return []
    
    async def backup(self):
        """Создать резервную копию базы данных"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{Config.BACKUP_DIR}/backup_{timestamp}.db"
            
            async with self.get_connection() as src:
                async with aiosqlite.connect(backup_path) as dst:
                    await src.backup(dst)
            
            logger.info(f"Резервная копия создана: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return None

# Инициализация базы данных
try:
    Config.validate()
    db = SupremeDatabase(Config.DB_FILE)
    logger.info("Конфигурация и база данных загружены успешно")
except Exception as e:
    logger.critical(f"Критическая ошибка инициализации: {e}")
    sys.exit(1)

# ============================================================================
# СИСТЕМА РАНГОВ - УЛУЧШЕННАЯ
# ============================================================================

class SupremeRankSystem:
    """Система рангов с бонусами и привилегиями"""
    
    RANKS = [
        (100000000, '🔥 ВЕЧНЫЙ ПОВЕЛИТЕЛЬ ГОТИЧЕСКОЙ КОБРЫ', '🔥', 2.0),
        (50000000, '💎 АПОКАЛИПТИЧЕСКАЯ КОРОЛЕВА ГАДЮК', '💎', 1.8),
        (10000000, '👑 КОСМИЧЕСКОЕ БОЖЕСТВО КОБРЫ', '👑', 1.6),
        (5000000, '🌟 МИФИЧЕСКИЙ ТИТАН ГАДЮКИ', '🌟', 1.5),
        (1000000, '⚡ ВЕРХОВНЫЙ БОГ КОБРЫ', '⚡', 1.4),
        (500000, '🔥 ЛЕГЕНДАРНЫЙ ПОВЕЛИТЕЛЬ ГАДЮКИ', '🔥', 1.3),
        (100000, '💫 ЗОЛОТОЙ ИМПЕРАТОР КОБРЫ', '💫', 1.2),
        (50000, '💎 АЛМАЗНАЯ ГАДЮКА', '💎', 1.15),
        (10000, '🏆 ПЛАТИНОВЫЙ ЗМЕЙ', '🏆', 1.1),
        (5000, '🪙 ЗОЛОТАЯ ГАДЮКА', '🪙', 1.05),
        (1000, '🥈 СЕРЕБРЯНЫЙ ЗМЕЙ', '🥈', 1.03),
        (100, '🪱 БРОНЗОВЫЙ ЧЕРВЬ', '🪱', 1.01),
        (0, '🐛 ЖАЛКИЙ НОВИЧОК', '🐛', 1.0)
    ]
    
    @classmethod
    def get_rank_info(cls, spent_stars: int) -> dict:
        """Получить информацию о ранге пользователя"""
        for threshold, name, emoji, multiplier in cls.RANKS:
            if spent_stars >= threshold:
                return {
                    'name': name,
                    'emoji': emoji,
                    'multiplier': multiplier,
                    'threshold': threshold
                }
        return cls.RANKS[-1]
    
    @classmethod
    def get_next_rank(cls, spent_stars: int) -> dict:
        """Получить следующий ранг"""
        for i, (threshold, name, emoji, multiplier) in enumerate(cls.RANKS):
            if spent_stars >= threshold:
                if i > 0:
                    next_threshold = cls.RANKS[i-1][0]
                    next_name = cls.RANKS[i-1][1]
                    next_emoji = cls.RANKS[i-1][2]
                    needed = next_threshold - spent_stars
                    return {
                        'name': next_name,
                        'emoji': next_emoji,
                        'needed': needed,
                        'threshold': next_threshold
                    }
        return {'name': 'MAX', 'emoji': '👑', 'needed': 0, 'threshold': spent_stars}
    
    @classmethod
    def calculate_bonus(cls, spent_stars: int, base_amount: int) -> int:
        """Рассчитать бонус на основе ранга"""
        rank_info = cls.get_rank_info(spent_stars)
        return int(base_amount * rank_info['multiplier'])

# ============================================================================
# СИСТЕМА ЯЗЫКОВ - ПОЛНОСТЬЮ ПЕРЕРАБОТАННАЯ
# ============================================================================

class SupremeLanguageSystem:
    """Улучшенная система языков с кэшированием"""
    
    TRANSLATIONS = {
        'EN': {
            'start': {
                'title': "🖤 **GOLDEN COBRA GOTH MOMMY: DOMINATE OR DIE!** 🖤",
                'welcome': "Welcome to the ultimate domination arena!",
                'instructions': "Spend stars, climb ranks, collect NFTs, and become the ultimate Cobra Emperor!"
            },
            'errors': {
                'not_enough_stars': "❌ Not enough stars! Earn more first!",
                'invalid_amount': "❌ Invalid amount! Must be positive number.",
                'user_not_found': "❌ User not found in shadows.",
                'cooldown': "⏳ Cooldown active! Wait {seconds} seconds.",
                'daily_claimed': "✅ Daily reward already claimed!",
                'challenge_self': "❌ You can't challenge yourself!"
            },
            'success': {
                'spend': "💥 **CARNAGE!** You spent {amount} ⭐! New rank: {rank}",
                'daily': "🎁 **DAILY REWARD!** +{amount} ⭐! Streak: {streak}",
                'challenge_sent': "⚔️ Challenge sent to @{username}!",
                'challenge_won': "🏆 **VICTORY!** You won {amount} ⭐!",
                'item_purchased': "🛒 **ITEM PURCHASED!** {item} added to your inventory!"
            },
            'buttons': {
                'spend': "💰 Spend Stars",
                'daily': "🎁 Daily Reward",
                'shop': "🛒 NFT Shop",
                'inventory': "🎒 Inventory",
                'leaderboard': "🏆 Leaderboard",
                'challenge': "⚔️ Challenge",
                'quests': "📜 Quests",
                'profile': "👤 Profile"
            }
        },
        'RU': {
            'start': {
                'title': "🖤 **GOLDEN COBRA ГОТИЧЕСКАЯ МАМОЧКА: ДОМИНИРУЙ ИЛИ УМРИ!** 🖤",
                'welcome': "Добро пожаловать на арену тотального доминирования!",
                'instructions': "Трать звезды, поднимайся в рангах, собирай NFT и стань императором Кобры!"
            },
            'errors': {
                'not_enough_stars': "❌ Недостаточно звезд! Заработай больше!",
                'invalid_amount': "❌ Неверное количество! Должно быть положительным числом.",
                'user_not_found': "❌ Пользователь не найден во тьме.",
                'cooldown': "⏳ Охлаждение активно! Подожди {seconds} секунд.",
                'daily_claimed': "✅ Ежедневная награда уже получена!",
                'challenge_self': "❌ Нельзя вызывать себя!"
            },
            'success': {
                'spend': "💥 **БОЙНЯ!** Ты потратил {amount} ⭐! Новый ранг: {rank}",
                'daily': "🎁 **ЕЖЕДНЕВНАЯ НАГРАДА!** +{amount} ⭐! Серия: {streak}",
                'challenge_sent': "⚔️ Вызов отправлен @{username}!",
                'challenge_won': "🏆 **ПОБЕДА!** Ты выиграл {amount} ⭐!",
                'item_purchased': "🛒 **ПРЕДМЕТ КУПЛЕН!** {item} добавлен в инвентарь!"
            },
            'buttons': {
                'spend': "💰 Потратить Звезды",
                'daily': "🎁 Ежедневная Награда",
                'shop': "🛒 NFT Магазин",
                'inventory': "🎒 Инвентарь",
                'leaderboard': "🏆 Таблица Лидеров",
                'challenge': "⚔️ Вызов",
                'quests': "📜 Квесты",
                'profile': "👤 Профиль"
            }
        }
    }
    
    @classmethod
    def get_text(cls, lang: str, category: str, key: str, **kwargs) -> str:
        """Получить переведенный текст"""
        try:
            text = cls.TRANSLATIONS.get(lang, cls.TRANSLATIONS['EN'])[category][key]
            if kwargs:
                return text.format(**kwargs)
            return text
        except KeyError:
            return f"[{category}.{key}]"

# ============================================================================
# СИСТЕМА КЭШИРОВАНИЯ - ВЫСОКОПРОИЗВОДИТЕЛЬНАЯ
# ============================================================================

class SupremeCache:
    """Система кэширования для максимальной производительности"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self.ttl = 300  # 5 минут
        
    def set(self, key: str, value: Any, ttl: int = None):
        """Сохранить значение в кэш"""
        self._cache[key] = value
        self._timestamps[key] = time.time() + (ttl or self.ttl)
        
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение из кэша"""
        if key in self._cache:
            if time.time() < self._timestamps.get(key, 0):
                return self._cache[key]
            else:
                # Удалить просроченный кэш
                del self._cache[key]
                del self._timestamps[key]
        return default
    
    def delete(self, key: str):
        """Удалить значение из кэша"""
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
    
    def clear(self):
        """Очистить весь кэш"""
        self._cache.clear()
        self._timestamps.clear()

# Инициализация кэша
cache = SupremeCache()

# ============================================================================
# ОСНОВНЫЕ КЛАССЫ БОТА
# ============================================================================

class SupremeBot:
    """Главный класс бота с улучшенной архитектурой"""
    
    def __init__(self):
        self.bot = Bot(
            token=Config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.router = Router()
        self.dp.include_router(self.router)
        
        # Инициализация состояний
        self.states = self.create_states()
        
        # Регистрация обработчиков
        self.register_handlers()
        
        logger.info("Supreme Bot initialized")
    
    class States(StatesGroup):
        """Состояния FSM"""
        await_spend = State()
        await_challenge = State()
        await_purchase = State()
        await_quest = State()
    
    def create_states(self):
        """Создание состояний"""
        return self.States()
    
    def register_handlers(self):
        """Регистрация всех обработчиков"""
        
        @self.router.message(Command("start"))
        async def cmd_start(message: Message, command: CommandObject = None):
            await self.handle_start(message, command)
        
        @self.router.message(Command("spend"))
        async def cmd_spend(message: Message, command: CommandObject = None):
            await self.handle_spend(message, command)
        
        @self.router.message(Command("daily"))
        async def cmd_daily(message: Message):
            await self.handle_daily(message)
        
        @self.router.message(Command("shop"))
        async def cmd_shop(message: Message):
            await self.handle_shop(message)
        
        @self.router.message(Command("profile"))
        async def cmd_profile(message: Message):
            await self.handle_profile(message)
        
        @self.router.message(Command("leaderboard"))
        async def cmd_leaderboard(message: Message):
            await self.handle_leaderboard(message)
        
        @self.router.message(Command("help"))
        async def cmd_help(message: Message):
            await self.handle_help(message)
        
        @self.router.message(Command("admin"))
        async def cmd_admin(message: Message, command: CommandObject = None):
            await self.handle_admin(message, command)
    
    async def handle_start(self, message: Message, command: CommandObject):
        """Обработка команды /start"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name
            
            # Реферальная система
            referral_bonus = 0
            if command and command.args:
                try:
                    referrer_id = int(command.args)
                    if referrer_id != user_id:
                        # Начисляем бонус рефереру
                        await db.execute(
                            "UPDATE users SET referrals = referrals + 1 WHERE user_id = ?",
                            (referrer_id,)
                        )
                        await db.execute(
                            "UPDATE users SET earned_stars = earned_stars + 100 WHERE user_id = ?",
                            (referrer_id,)
                        )
                        await db.execute(
                            "UPDATE users SET referral_id = ? WHERE user_id = ?",
                            (referrer_id, user_id)
                        )
                        referral_bonus = 100
                except ValueError:
                    pass
            
            # Создание/обновление пользователя
            await db.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_active) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, message.from_user.first_name))
            
            # Приветственное сообщение
            keyboard = self.create_main_keyboard('EN')
            
            welcome_text = """
🖤 **WELCOME TO GOLDEN COBRA SUPREME!** 🖤

*Your journey to domination begins now!*

💎 *Features:*
• Spend stars to climb ranks
• Collect rare NFTs
• Challenge other players
• Complete quests for rewards
• Compete for top positions

⚡ *Quick Start:*
1. Use /daily for free stars
2. Spend stars with /spend
3. Check /shop for NFTs
4. View /leaderboard

🔥 *Become the ultimate Cobra Emperor!*
            """
            
            if referral_bonus:
                welcome_text += f"\n\n🎁 **Referral Bonus:** +{referral_bonus} ⭐"
            
            await message.answer(welcome_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            await message.answer("❌ Error initializing your profile. Please try again.")
    
    async def handle_spend(self, message: Message, command: CommandObject):
        """Обработка команды /spend"""
        try:
            user_id = message.from_user.id
            
            if command and command.args:
                try:
                    amount = int(command.args)
                    if amount < Config.MIN_STARS_PER_TRANSACTION:
                        await message.answer(f"❌ Minimum amount is {Config.MIN_STARS_PER_TRANSACTION} ⭐")
                        return
                    
                    if amount > Config.MAX_STARS_PER_TRANSACTION:
                        await message.answer(f"❌ Maximum amount is {Config.MAX_STARS_PER_TRANSACTION} ⭐")
                        return
                    
                    # Проверяем баланс
                    user = await db.fetchone(
                        "SELECT earned_stars FROM users WHERE user_id = ?",
                        (user_id,)
                    )
                    
                    if not user or user['earned_stars'] < amount:
                        await message.answer("❌ Not enough stars! Use /daily to get more.")
                        return
                    
                    # Обновляем баланс
                    await db.execute('''
                        UPDATE users 
                        SET spent_stars = spent_stars + ?,
                            earned_stars = earned_stars - ?
                        WHERE user_id = ?
                    ''', (amount, amount, user_id))
                    
                    # Обновляем глобальный фонд
                    await db.execute(
                        "UPDATE global_fund SET total_stars = total_stars + ? WHERE id = 1",
                        (amount,)
                    )
                    
                    # Записываем транзакцию
                    await db.execute('''
                        INSERT INTO transactions (user_id, amount, type, description)
                        VALUES (?, ?, 'spend', ?)
                    ''', (user_id, amount, f"Spent {amount} stars"))
                    
                    # Получаем новый ранг
                    user_data = await db.fetchone(
                        "SELECT spent_stars FROM users WHERE user_id = ?",
                        (user_id,)
                    )
                    
                    rank_info = SupremeRankSystem.get_rank_info(user_data['spent_stars'])
                    
                    # Отправляем сообщение об успехе
                    success_text = f"""
💥 **STARS SPENT SUCCESSFULLY!** 💥

⭐ Amount: {amount} stars
👑 New Rank: {rank_info['emoji']} {rank_info['name']}
🔥 Multiplier: x{rank_info['multiplier']}

*Keep spending to reach higher ranks!*
                    """
                    
                    await message.answer(success_text)
                    
                    # Проверяем достижения
                    await self.check_achievements(user_id)
                    
                    # Проверяем квесты
                    await self.check_quests(user_id, 'spend', amount)
                    
                except ValueError:
                    await message.answer("❌ Invalid amount! Usage: /spend <amount>")
            else:
                await message.answer("💰 Enter amount of stars to spend:\n\nUsage: `/spend 1000`")
                
        except Exception as e:
            logger.error(f"Error in handle_spend: {e}")
            await message.answer("❌ Error processing your request. Please try again.")
    
    async def handle_daily(self, message: Message):
        """Обработка команды /daily"""
        try:
            user_id = message.from_user.id
            
            # Проверяем время последнего получения
            user = await db.fetchone(
                "SELECT last_daily_claim, daily_streak FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            now = datetime.now()
            can_claim = True
            
            if user and user['last_daily_claim']:
                last_claim = datetime.fromisoformat(user['last_daily_claim'].replace('Z', '+00:00'))
                hours_since = (now - last_claim).total_seconds() / 3600
                
                if hours_since < Config.DAILY_COOLDOWN_HOURS:
                    can_claim = False
                    remaining = Config.DAILY_COOLDOWN_HOURS - hours_since
                    await message.answer(f"⏳ Come back in {int(remaining)} hours!")
                    return
            
            # Рассчитываем награду
            if user and user['daily_streak']:
                streak = user['daily_streak']
                if can_claim:
                    new_streak = streak + 1
                else:
                    new_streak = 1
            else:
                new_streak = 1
            
            # Базовая награда + бонус за серию
            base_reward = 100
            streak_bonus = min(new_streak * 10, 500)  # Макс 500
            total_reward = base_reward + streak_bonus
            
            # Начисляем награду
            await db.execute('''
                UPDATE users 
                SET earned_stars = earned_stars + ?,
                    daily_streak = ?,
                    last_daily_claim = ?
                WHERE user_id = ?
            ''', (total_reward, new_streak, now.isoformat(), user_id))
            
            # Записываем транзакцию
            await db.execute('''
                INSERT INTO transactions (user_id, amount, type, description)
                VALUES (?, ?, 'daily', ?)
            ''', (user_id, total_reward, f"Daily reward (streak: {new_streak})"))
            
            # Отправляем сообщение
            daily_text = f"""
🎁 **DAILY REWARD COLLECTED!** 🎁

⭐ Stars Received: {total_reward}
📈 Daily Streak: {new_streak} days
🔥 Streak Bonus: +{streak_bonus} stars

*Come back tomorrow for even more!*
            """
            
            await message.answer(daily_text)
            
        except Exception as e:
            logger.error(f"Error in handle_daily: {e}")
            await message.answer("❌ Error claiming daily reward. Please try again.")
    
    async def handle_shop(self, message: Message):
        """Обработка команды /shop"""
        try:
            # Получаем товары из магазина
            items = await db.fetchall(
                "SELECT * FROM shop_items WHERE available = 1 ORDER BY price"
            )
            
            if not items:
                await message.answer("🛒 Shop is currently empty!")
                return
            
            # Создаем клавиатуру магазина
            keyboard = InlineKeyboardBuilder()
            
            shop_text = "🛒 **GOLDEN COBRA NFT SHOP** 🛒\n\n"
            
            for item in items:
                stock_info = f" ({item['stock']} left)" if item['stock'] > 0 else ""
                shop_text += f"{item['emoji']} **{item['name']}**\n"
                shop_text += f"*{item['description']}*\n"
                shop_text += f"💰 Price: {item['price']} ⭐ [{item['rarity']}]{stock_info}\n"
                shop_text += f"🆔 ID: `{item['id']}`\n\n"
                
                # Кнопка для покупки
                keyboard.button(
                    text=f"{item['emoji']} Buy {item['name']} - {item['price']}⭐",
                    callback_data=f"buy_{item['id']}"
                )
            
            keyboard.adjust(1)
            shop_text += "\n*Use `/buy <item_id>` to purchase an item.*"
            
            await message.answer(shop_text, reply_markup=keyboard.as_markup())
            
        except Exception as e:
            logger.error(f"Error in handle_shop: {e}")
            await message.answer("❌ Error loading shop. Please try again.")
    
    async def handle_profile(self, message: Message):
        """Обработка команды /profile"""
        try:
            user_id = message.from_user.id
            
            # Получаем данные пользователя
            user = await db.fetchone('''
                SELECT u.*, 
                       (SELECT COUNT(*) FROM inventory WHERE user_id = u.user_id) as nft_count,
                       (SELECT COUNT(*) FROM user_achievements WHERE user_id = u.user_id) as achievements_count
                FROM users u 
                WHERE user_id = ?
            ''', (user_id,))
            
            if not user:
                await message.answer("❌ User profile not found!")
                return
            
            # Получаем позицию в рейтинге
            position = await db.fetchone('''
                SELECT COUNT(*) + 1 as position 
                FROM users 
                WHERE spent_stars > ? AND is_banned = 0
            ''', (user['spent_stars'],))
            
            # Получаем информацию о ранге
            rank_info = SupremeRankSystem.get_rank_info(user['spent_stars'])
            next_rank = SupremeRankSystem.get_next_rank(user['spent_stars'])
            
            # Строим текст профиля
            profile_text = f"""
👤 **YOUR PROFILE** 👤

*Basic Information:*
🆔 ID: `{user['user_id']}`
👤 Username: @{user['username'] or 'No username'}
📅 Joined: {user['created_at'][:10] if user['created_at'] else 'Recently'}

*Statistics:*
⭐ Spent Stars: {user['spent_stars']:,}
💰 Earned Stars: {user['earned_stars']:,}
📈 Global Rank: #{position['position'] if position else 'N/A'}
👥 Referrals: {user['referrals']}
📅 Daily Streak: {user['daily_streak']} days

*Rank Information:*
{rank_info['emoji']} **Current Rank:** {rank_info['name']}
⚡ **Rank Multiplier:** x{rank_info['multiplier']}
🎯 **Next Rank:** {next_rank['name']}
📊 **Stars Needed:** {next_rank['needed']:,}

*Collections:*
🖼️ NFTs Collected: {user['nft_count']}
🏆 Achievements: {user['achievements_count']}

*Keep dominating to improve your stats!*
            """
            
            await message.answer(profile_text)
            
        except Exception as e:
            logger.error(f"Error in handle_profile: {e}")
            await message.answer("❌ Error loading profile. Please try again.")
    
    async def handle_leaderboard(self, message: Message):
        """Обработка команды /leaderboard"""
        try:
            # Получаем топ-10 пользователей
            top_users = await db.fetchall('''
                SELECT user_id, username, spent_stars, earned_stars 
                FROM users 
                WHERE is_banned = 0 
                ORDER BY spent_stars DESC 
                LIMIT 10
            ''')
            
            if not top_users:
                await message.answer("🏆 Leaderboard is empty!")
                return
            
            # Получаем глобальный фонд
            fund = await db.fetchone("SELECT * FROM global_fund WHERE id = 1")
            
            # Строим текст лидерборда
            leaderboard_text = "🏆 **GLOBAL LEADERBOARD** 🏆\n\n"
            
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            
            for i, user in enumerate(top_users):
                username = user['username'] or f"User{user['user_id']}"
                leaderboard_text += f"{medals[i]} **{username}**\n"
                leaderboard_text += f"   ⭐ Spent: {user['spent_stars']:,}\n"
                leaderboard_text += f"   💰 Balance: {user['earned_stars']:,}\n\n"
            
            if fund:
                progress = (fund['total_stars'] / fund['current_goal']) * 100
                leaderboard_text += f"🌍 **Global Fund:** {fund['total_stars']:,}/{fund['current_goal']:,} ⭐ ({progress:.1f}%)\n"
                leaderboard_text += f"🎯 **Next Goal:** {fund['next_goal']:,} ⭐\n"
            
            leaderboard_text += "\n*Spend stars to climb the ranks!*"
            
            await message.answer(leaderboard_text)
            
        except Exception as e:
            logger.error(f"Error in handle_leaderboard: {e}")
            await message.answer("❌ Error loading leaderboard. Please try again.")
    
    async def handle_help(self, message: Message):
        """Обработка команды /help"""
        help_text = """
🖤 **GOLDEN COBRA SUPREME - HELP** 🖤

*Basic Commands:*
/start - Start the bot
/profile - View your profile
/leaderboard - Global leaderboard
/help - Show this message

*Star Management:*
/spend <amount> - Spend stars
/daily - Claim daily reward
/shop - NFT shop
/inventory - Your items

*Game Features:*
/challenge @user <amount> - Challenge another player
/quests - View available quests
/achievements - Your achievements

*Administration:*
/admin stats - Bot statistics
/admin backup - Create backup
/admin announce <text> - Global announcement

*Need more help? Contact support!*
        """
        
        await message.answer(help_text)
    
    async def handle_admin(self, message: Message, command: CommandObject):
        """Обработка административных команд"""
        try:
            user_id = message.from_user.id
            
            if user_id not in Config.ADMIN_IDS:
                await message.answer("❌ Access denied!")
                return
            
            if not command or not command.args:
                admin_text = """
🛡️ **ADMIN PANEL** 🛡️

*Available Commands:*
/admin stats - Show bot statistics
/admin backup - Create database backup
/admin announce <text> - Send global announcement
/admin addstars <user_id> <amount> - Add stars to user
/admin resetdaily - Reset all daily claims
/admin ban <user_id> <reason> - Ban user
/admin unban <user_id> - Unban user
                """
                await message.answer(admin_text)
                return
            
            args = command.args.split()
            cmd = args[0].lower()
            
            if cmd == "stats":
                # Статистика бота
                stats = await self.get_bot_stats()
                await message.answer(stats)
                
            elif cmd == "backup":
                # Создание бэкапа
                backup_path = await db.backup()
                if backup_path:
                    await message.answer(f"✅ Backup created: `{backup_path}`")
                else:
                    await message.answer("❌ Backup failed!")
            
            elif cmd == "announce":
                # Глобальное объявление
                if len(args) < 2:
                    await message.answer("Usage: /admin announce <text>")
                    return
                
                announcement = " ".join(args[1:])
                sent = await self.send_global_announcement(announcement)
                await message.answer(f"✅ Announcement sent to {sent} users")
            
            elif cmd == "addstars":
                # Добавление звезд
                if len(args) < 3:
                    await message.answer("Usage: /admin addstars <user_id> <amount>")
                    return
                
                try:
                    target_id = int(args[1])
                    amount = int(args[2])
                    
                    await db.execute(
                        "UPDATE users SET earned_stars = earned_stars + ? WHERE user_id = ?",
                        (amount, target_id)
                    )
                    
                    await message.answer(f"✅ Added {amount} ⭐ to user {target_id}")
                    
                    # Уведомляем пользователя
                    try:
                        await self.bot.send_message(
                            target_id,
                            f"🎁 **ADMIN BONUS!** You received {amount} ⭐ from administration!"
                        )
                    except:
                        pass
                        
                except ValueError:
                    await message.answer("❌ Invalid user_id or amount!")
            
            elif cmd == "resetdaily":
                # Сброс daily наград
                await db.execute("UPDATE users SET last_daily_claim = NULL")
                await message.answer("✅ All daily claims reset!")
            
            else:
                await message.answer("❌ Unknown admin command!")
                
        except Exception as e:
            logger.error(f"Error in handle_admin: {e}")
            await message.answer("❌ Admin command failed!")
    
    async def get_bot_stats(self) -> str:
        """Получить статистику бота"""
        try:
            # Основная статистика
            total_users = await db.fetchone("SELECT COUNT(*) as count FROM users")
            active_users = await db.fetchone('''
                SELECT COUNT(*) as count FROM users 
                WHERE datetime(last_active) > datetime('now', '-7 days')
            ''')
            
            total_spent = await db.fetchone("SELECT SUM(spent_stars) as total FROM users")
            total_earned = await db.fetchone("SELECT SUM(earned_stars) as total FROM users")
            
            # Статистика вызовов
            total_challenges = await db.fetchone(
                "SELECT COUNT(*) as count FROM challenges WHERE status = 'completed'"
            )
            
            # Статистика магазина
            items_sold = await db.fetchone("SELECT COUNT(*) as count FROM inventory")
            
            # Глобальный фонд
            fund = await db.fetchone("SELECT * FROM global_fund WHERE id = 1")
            
            stats_text = f"""
📊 **BOT STATISTICS** 📊

*Users:*
👥 Total Users: {total_users['count'] if total_users else 0}
🚀 Active (7 days): {active_users['count'] if active_users else 0}

*Stars Economy:*
⭐ Total Spent: {total_spent['total'] if total_spent and total_spent['total'] else 0:,}
💰 Total Earned: {total_earned['total'] if total_earned and total_earned['total'] else 0:,}

*Game Activity:*
⚔️ Completed Challenges: {total_challenges['count'] if total_challenges else 0}
🛒 Items Sold: {items_sold['count'] if items_sold else 0}

*Global Fund:*
🌍 Current: {fund['total_stars'] if fund else 0:,}/{fund['current_goal'] if fund else 0:,}
🎯 Next Goal: {fund['next_goal'] if fund else 0:,}
🎉 Raffles: {fund['total_raffles'] if fund else 0}

*Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
            """
            
            return stats_text
            
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return "❌ Error loading statistics"
    
    async def send_global_announcement(self, text: str) -> int:
        """Отправить глобальное объявление"""
        try:
            users = await db.fetchall("SELECT user_id FROM users WHERE is_banned = 0")
            
            sent = 0
            announcement = f"📢 **GLOBAL ANNOUNCEMENT**\n\n{text}\n\n- Golden Cobra Team 🖤"
            
            for user in users:
                try:
                    await self.bot.send_message(user['user_id'], announcement)
                    sent += 1
                    await asyncio.sleep(0.05)  # Rate limiting
                except Exception as e:
                    logger.debug(f"Failed to send to {user['user_id']}: {e}")
            
            return sent
            
        except Exception as e:
            logger.error(f"Error sending announcement: {e}")
            return 0
    
    async def check_achievements(self, user_id: int):
        """Проверить и разблокировать достижения"""
        try:
            # Получаем статистику пользователя
            user = await db.fetchone('''
                SELECT spent_stars, earned_stars, daily_streak, referrals,
                       (SELECT COUNT(*) FROM challenges WHERE winner_id = ?) as challenges_won,
                       (SELECT COUNT(DISTINCT item_id) FROM inventory WHERE user_id = ?) as nft_count
                FROM users WHERE user_id = ?
            ''', (user_id, user_id, user_id))
            
            if not user:
                return
            
            # Получаем все достижения
            achievements = await db.fetchall("SELECT * FROM achievements")
            
            for achievement in achievements:
                # Проверяем, уже ли разблокировано
                unlocked = await db.fetchone(
                    "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
                    (user_id, achievement['id'])
                )
                
                if unlocked:
                    continue
                
                # Проверяем условие
                condition_met = False
                condition_type = achievement['condition_type']
                condition_value = achievement['condition_value']
                
                if condition_type == 'spend' and user['spent_stars'] >= condition_value:
                    condition_met = True
                elif condition_type == 'earned' and user['earned_stars'] >= condition_value:
                    condition_met = True
                elif condition_type == 'daily_streak' and user['daily_streak'] >= condition_value:
                    condition_met = True
                elif condition_type == 'referral' and user['referrals'] >= condition_value:
                    condition_met = True
                elif condition_type == 'challenge_win' and user['challenges_won'] >= condition_value:
                    condition_met = True
                elif condition_type == 'nft_count' and user['nft_count'] >= condition_value:
                    condition_met = True
                
                if condition_met:
                    # Разблокируем достижение
                    await db.execute(
                        "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
                        (user_id, achievement['id'])
                    )
                    
                    # Награждаем звездами
                    if achievement['reward_stars'] > 0:
                        await db.execute(
                            "UPDATE users SET earned_stars = earned_stars + ? WHERE user_id = ?",
                            (achievement['reward_stars'], user_id)
                        )
                    
                    # Уведомляем пользователя
                    try:
                        await self.bot.send_message(
                            user_id,
                            f"🏆 **ACHIEVEMENT UNLOCKED!**\n\n"
                            f"{achievement['emoji']} *{achievement['name']}*\n"
                            f"{achievement['description']}\n\n"
                            f"🎁 Reward: +{achievement['reward_stars']} ⭐"
                        )
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
    
    async def check_quests(self, user_id: int, quest_type: str, value: int = 1):
        """Проверить и обновить квесты"""
        try:
            # Получаем активные квесты
            quests = await db.fetchall(
                "SELECT * FROM quests WHERE is_active = 1"
            )
            
            for quest in quests:
                # Проверяем тип квеста
                if quest['requirement_type'] != quest_type:
                    continue
                
                # Получаем прогресс
                progress = await db.fetchone('''
                    SELECT * FROM quest_progress 
                    WHERE user_id = ? AND quest_id = ? AND completed = 0
                ''', (user_id, quest['id']))
                
                if not progress:
                    # Создаем новый прогресс
                    await db.execute('''
                        INSERT INTO quest_progress (user_id, quest_id, progress)
                        VALUES (?, ?, ?)
                    ''', (user_id, quest['id'], value))
                else:
                    # Обновляем прогресс
                    new_progress = progress['progress'] + value
                    await db.execute('''
                        UPDATE quest_progress 
                        SET progress = ? 
                        WHERE user_id = ? AND quest_id = ?
                    ''', (new_progress, user_id, quest['id']))
                
                # Проверяем завершение
                updated_progress = await db.fetchone('''
                    SELECT progress FROM quest_progress 
                    WHERE user_id = ? AND quest_id = ?
                ''', (user_id, quest['id']))
                
                if updated_progress and updated_progress['progress'] >= quest['requirement_value']:
                    # Завершаем квест
                    await db.execute('''
                        UPDATE quest_progress 
                        SET completed = 1, completed_at = CURRENT_TIMESTAMP 
                        WHERE user_id = ? AND quest_id = ?
                    ''', (user_id, quest['id']))
                    
                    # Награждаем пользователя
                    await db.execute(
                        "UPDATE users SET earned_stars = earned_stars + ? WHERE user_id = ?",
                        (quest['reward_stars'], user_id)
                    )
                    
                    # Уведомляем
                    try:
                        await self.bot.send_message(
                            user_id,
                            f"🎯 **QUEST COMPLETED!**\n\n"
                            f"📜 *{quest['name']}*\n"
                            f"{quest['description']}\n\n"
                            f"🎁 Reward: +{quest['reward_stars']} ⭐"
                        )
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error checking quests: {e}")
    
    def create_main_keyboard(self, lang: str = 'EN') -> InlineKeyboardMarkup:
        """Создать основную клавиатуру"""
        keyboard = InlineKeyboardBuilder()
        
        buttons = [
            ("💰 Spend Stars", "spend"),
            ("🎁 Daily Reward", "daily"),
            ("🛒 NFT Shop", "shop"),
            ("🎒 Inventory", "inventory"),
            ("🏆 Leaderboard", "leaderboard"),
            ("⚔️ Challenge", "challenge"),
            ("📜 Quests", "quests"),
            ("👤 Profile", "profile"),
        ]
        
        for text, callback in buttons:
            keyboard.button(text=text, callback_data=callback)
        
        keyboard.adjust(2)
        return keyboard.as_markup()
    
    async def start(self):
        """Запуск бота"""
        logger.info("Starting Supreme Bot...")
        
        # Запускаем фоновые задачи
        asyncio.create_task(self.background_tasks())
        
        # Запускаем бота
        await self.dp.start_polling(self.bot)
    
    async def background_tasks(self):
        """Фоновые задачи"""
        while True:
            try:
                # Проверяем истекшие вызовы
                await self.check_expired_challenges()
                
                # Проверяем достижения глобального фонда
                await self.check_global_fund()
                
                # Отправляем напоминания
                await self.send_reminders()
                
                # Очищаем старые логи
                await self.cleanup_old_data()
                
                await asyncio.sleep(300)  # 5 минут
                
            except Exception as e:
                logger.error(f"Error in background tasks: {e}")
                await asyncio.sleep(60)
    
    async def check_expired_challenges(self):
        """Проверить истекшие вызовы"""
        try:
            expired = await db.fetchall('''
                SELECT * FROM challenges 
                WHERE status = 'pending' 
                AND datetime(expires_at) < datetime('now')
            ''')
            
            for challenge in expired:
                await db.execute(
                    "UPDATE challenges SET status = 'expired' WHERE id = ?",
                    (challenge['id'],)
                )
                
        except Exception as e:
            logger.error(f"Error checking expired challenges: {e}")
    
    async def check_global_fund(self):
        """Проверить достижение цели глобального фонда"""
        try:
            fund = await db.fetchone("SELECT * FROM global_fund WHERE id = 1")
            
            if fund and fund['total_stars'] >= fund['current_goal'] and not fund['raffle_active']:
                # Запускаем розыгрыш
                await self.start_raffle(fund['current_goal'])
                
        except Exception as e:
            logger.error(f"Error checking global fund: {e}")
    
    async def start_raffle(self, goal: int):
        """Запустить розыгрыш"""
        try:
            # Помечаем розыгрыш активным
            await db.execute(
                "UPDATE global_fund SET raffle_active = 1 WHERE id = 1"
            )
            
            # Получаем активных пользователей
            active_users = await db.fetchall('''
                SELECT user_id FROM users 
                WHERE datetime(last_active) > datetime('now', '-30 days')
                AND is_banned = 0
            ''')
            
            if not active_users:
                return
            
            # Выбираем победителей (10% активных пользователей, минимум 1, максимум 10)
            num_winners = max(1, min(len(active_users) // 10, 10))
            winners = random.sample([u['user_id'] for u in active_users], num_winners)
            
            # Приз на каждого победителя
            prize_per_winner = goal // (num_winners * 2)
            
            for winner_id in winners:
                await db.execute(
                    "UPDATE users SET earned_stars = earned_stars + ? WHERE user_id = ?",
                    (prize_per_winner, winner_id)
                )
                
                # Уведомляем победителя
                try:
                    await self.bot.send_message(
                        winner_id,
                        f"🎉 **RAFFLE WINNER!** 🎉\n\n"
                        f"Global goal of {goal:,} ⭐ reached!\n"
                        f"You won {prize_per_winner} ⭐!\n\n"
                        f"Congratulations! 🖤"
                    )
                except:
                    pass
            
            # Обновляем глобальный фонд
            await db.execute('''
                UPDATE global_fund 
                SET raffle_active = 0,
                    last_raffle = CURRENT_TIMESTAMP,
                    total_raffles = total_raffles + 1,
                    current_goal = next_goal,
                    next_goal = next_goal * 2
                WHERE id = 1
            ''')
            
            # Отправляем объявление
            await self.send_global_announcement(
                f"🎉 **RAFFLE COMPLETE!** 🎉\n\n"
                f"Global goal of {goal:,} ⭐ reached!\n"
                f"Winners: {num_winners} lucky warriors\n"
                f"Prize per winner: {prize_per_winner} ⭐\n\n"
                f"Next goal: {goal * 2:,} ⭐\n"
                f"Keep bleeding stars! 🖤🔥"
            )
            
        except Exception as e:
            logger.error(f"Error starting raffle: {e}")
    
    async def send_reminders(self):
        """Отправить напоминания неактивным пользователям"""
        try:
            inactive_users = await db.fetchall('''
                SELECT user_id, username, spent_stars 
                FROM users 
                WHERE datetime(last_active) < datetime('now', '-1 day')
                AND is_banned = 0
                LIMIT 50
            ''')
            
            for user in inactive_users:
                # Получаем топ пользователя
                top_user = await db.fetchone('''
                    SELECT username, spent_stars FROM users 
                    WHERE is_banned = 0 
                    ORDER BY spent_stars DESC 
                    LIMIT 1
                ''')
                
                if top_user:
                    gap = top_user['spent_stars'] - user['spent_stars'] + 1
                    
                    reminder = f"""
🖤 **HEY, @{user['username']}!** 🖤

You're {gap:,} ⭐ behind the leader @{top_user['username']}!

💀 **Goth Mommy commands you:** 
Spend NOW or face eternal shame!

🔥 **Quick actions:**
• /daily - Get free stars
• /spend 1000 - Spend stars
• /challenge - Fight for glory

*No mercy for the weak!* 💀💰
                    """
                    
                    try:
                        await self.bot.send_message(user['user_id'], reminder)
                        await asyncio.sleep(1)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error sending reminders: {e}")
    
    async def cleanup_old_data(self):
        """Очистка старых данных"""
        try:
            # Удаляем старые транзакции (старше 30 дней)
            await db.execute('''
                DELETE FROM transactions 
                WHERE datetime(created_at) < datetime('now', '-30 days')
            ''')
            
            # Удаляем старые завершенные вызовы
            await db.execute('''
                DELETE FROM challenges 
                WHERE status IN ('completed', 'expired', 'declined')
                AND datetime(created_at) < datetime('now', '-7 days')
            ''')
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

# ============================================================================
# WEB INTERFACE - ULTIMATE EDITION
# ============================================================================

class SupremeWebApp:
    """Улучшенное веб-приложение"""
    
    def __init__(self, bot_instance: SupremeBot):
        self.app = FastAPI(
            title="Golden Cobra Supreme",
            description="Ultimate Aggressive Telegram Bot Web Interface",
            version="4.0.0"
        )
        
        self.bot = bot_instance
        self.setup_middleware()
        self.setup_routes()
        
        logger.info("Supreme Web App initialized")
    
    def setup_middleware(self):
        """Настройка middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Настройка маршрутов"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            return self.get_homepage()
        
        @self.app.get("/api/user/{user_id}")
        async def get_user(user_id: int):
            return await self.api_get_user(user_id)
        
        @self.app.post("/api/spend")
        async def spend_stars(request: Request):
            return await self.api_spend_stars(request)
        
        @self.app.get("/api/leaderboard")
        async def get_leaderboard(limit: int = 10):
            return await self.api_get_leaderboard(limit)
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def get_homepage(self) -> str:
        """Главная страница веб-интерфейса"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🖤 Golden Cobra Supreme 🖤</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000;
            color: #ffd700;
            font-family: 'Arial Black', sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }
        
        header {
            text-align: center;
            padding: 40px 0;
            background: linear-gradient(90deg, #000, #8b0000, #000);
            border-bottom: 5px solid #ffd700;
            margin-bottom: 40px;
            animation: headerGlow 3s infinite alternate;
        }
        
        @keyframes headerGlow {
            0% { box-shadow: 0 0 50px #ff0000; }
            100% { box-shadow: 0 0 100px #ffd700; }
        }
        
        h1 {
            font-size: 3.5rem;
            text-shadow: 0 0 30px #ff0000;
            margin-bottom: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .subtitle {
            font-size: 1.5rem;
            color: #ff6b6b;
            margin-bottom: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        
        .stat-card {
            background: rgba(139, 0, 0, 0.3);
            border: 3px solid #ffd700;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s;
            animation: cardFloat 6s infinite alternate;
        }
        
        @keyframes cardFloat {
            0% { transform: translateY(0); }
            100% { transform: translateY(-10px); }
        }
        
        .stat-card:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px #ff0000;
        }
        
        .stat-value {
            font-size: 2.5rem;
            color: #ffd700;
            text-shadow: 0 0 10px #ff0000;
            margin: 10px 0;
        }
        
        .stat-label {
            font-size: 1rem;
            color: #ff6b6b;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin: 50px 0;
        }
        
        .feature {
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid #8b0000;
            border-radius: 10px;
            padding: 25px;
            text-align: center;
        }
        
        .feature-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }
        
        .feature-title {
            font-size: 1.5rem;
            color: #ffd700;
            margin-bottom: 10px;
        }
        
        .feature-description {
            color: #ccc;
            line-height: 1.6;
        }
        
        .cta {
            text-align: center;
            margin: 60px 0;
            padding: 40px;
            background: linear-gradient(45deg, #000, #8b0000);
            border-radius: 20px;
            border: 5px solid #ffd700;
        }
        
        .cta-button {
            display: inline-block;
            background: linear-gradient(45deg, #ffd700, #ff0000);
            color: #000;
            padding: 15px 40px;
            font-size: 1.5rem;
            font-weight: bold;
            text-decoration: none;
            border-radius: 50px;
            margin-top: 20px;
            transition: all 0.3s;
            animation: buttonGlow 2s infinite alternate;
        }
        
        @keyframes buttonGlow {
            0% { box-shadow: 0 0 20px #ffd700; }
            100% { box-shadow: 0 0 40px #ff0000; }
        }
        
        .cta-button:hover {
            transform: scale(1.1);
            animation: none;
        }
        
        footer {
            text-align: center;
            padding: 30px;
            margin-top: 50px;
            border-top: 3px solid #8b0000;
            color: #666;
        }
        
        .snake-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.1;
        }
        
        .snake {
            position: absolute;
            font-size: 2rem;
            animation: snakeMove 20s linear infinite;
        }
        
        @keyframes snakeMove {
            0% { transform: translateX(-100px) rotate(0deg); }
            100% { transform: translateX(calc(100vw + 100px)) rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 2.5rem; }
            .stat-value { font-size: 2rem; }
            .features { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="snake-animation" id="snakes"></div>
    
    <div class="container">
        <header>
            <h1>🖤 GOLDEN COBRA SUPREME 🖤</h1>
            <div class="subtitle">ULTIMATE DOMINATION BOT - v4.0</div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Users</div>
                <div class="stat-value" id="totalUsers">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Stars Spent</div>
                <div class="stat-value" id="totalStars">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Players</div>
                <div class="stat-value" id="activePlayers">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">NFTs Sold</div>
                <div class="stat-value" id="nftsSold">0</div>
            </div>
        </div>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">💰</div>
                <div class="feature-title">Star Economy</div>
                <div class="feature-description">
                    Spend, earn, and dominate with our unique star economy system.
                    Climb ranks and become the ultimate Cobra Emperor.
                </div>
            </div>
            
            <div class="feature">
                <div class="feature-icon">🛒</div>
                <div class="feature-title">NFT Collection</div>
                <div class="feature-description">
                    Collect rare NFTs, trade with other players, and build your
                    ultimate collection of dark artifacts.
                </div>
            </div>
            
            <div class="feature">
                <div class="feature-icon">⚔️</div>
                <div class="feature-title">Challenges</div>
                <div class="feature-description">
                    Challenge other players in epic duels. Winner takes all!
                    Prove your dominance in the arena.
                </div>
            </div>
            
            <div class="feature">
                <div class="feature-icon">🏆</div>
                <div class="feature-title">Leaderboards</div>
                <div class="feature-description">
                    Compete for top positions in global leaderboards.
                    Your name in lights for all to see!
                </div>
            </div>
        </div>
        
        <div class="cta">
            <h2>READY TO DOMINATE?</h2>
            <p>Join thousands of players in the ultimate domination experience.</p>
            <a href="https://t.me/GoldenCobraSupremeBot" class="cta-button" target="_blank">
                🚀 START PLAYING NOW
            </a>
        </div>
        
        <footer>
            <p>🖤 Golden Cobra Supreme v4.0 | Ultimate Aggressive Telegram Bot</p>
            <p>© 2024 All rights reserved | Made with 💀 by Goth Mommy</p>
        </footer>
    </div>
    
    <script>
        // Создаем плавающих змей
        function createSnakes() {
            const container = document.getElementById('snakes');
            const snakes = ['🐍', '💀', '🔥', '💰', '👑', '⚡'];
            
            for (let i = 0; i < 15; i++) {
                const snake = document.createElement('div');
                snake.className = 'snake';
                snake.textContent = snakes[Math.floor(Math.random() * snakes.length)];
                snake.style.top = `${Math.random() * 100}%`;
                snake.style.animationDelay = `${Math.random() * 20}s`;
                snake.style.animationDuration = `${15 + Math.random() * 20}s`;
                snake.style.fontSize = `${1 + Math.random() * 3}rem`;
                container.appendChild(snake);
            }
        }
        
        // Загружаем статистику
        async function loadStats() {
            try {
                const response = await fetch('/api/leaderboard?limit=1');
                const data = await response.json();
                
                // Здесь можно обновить статистику на странице
                // В реальном проекте нужно добавить дополнительные эндпоинты
                
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        // Инициализация
        document.addEventListener('DOMContentLoaded', () => {
            createSnakes();
            loadStats();
            
            // Автообновление каждые 30 секунд
            setInterval(loadStats, 30000);
        });
    </script>
</body>
</html>
        """
    
    async def api_get_user(self, user_id: int):
        """API: Получить данные пользователя"""
        try:
            user = await db.fetchone('''
                SELECT u.*, 
                       (SELECT COUNT(*) FROM inventory WHERE user_id = u.user_id) as nft_count,
                       (SELECT COUNT(*) FROM user_achievements WHERE user_id = u.user_id) as achievements_count
                FROM users u 
                WHERE user_id = ?
            ''', (user_id,))
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Позиция в рейтинге
            position = await db.fetchone('''
                SELECT COUNT(*) + 1 as position 
                FROM users 
                WHERE spent_stars > ? AND is_banned = 0
            ''', (user['spent_stars'],))
            
            # Ранг
            rank_info = SupremeRankSystem.get_rank_info(user['spent_stars'])
            
            return {
                "user_id": user['user_id'],
                "username": user['username'],
                "spent_stars": user['spent_stars'],
                "earned_stars": user['earned_stars'],
                "daily_streak": user['daily_streak'],
                "rank": rank_info['name'],
                "rank_emoji": rank_info['emoji'],
                "position": position['position'] if position else 0,
                "referrals": user['referrals'],
                "nft_count": user['nft_count'],
                "achievements_count": user['achievements_count'],
                "created_at": user['created_at'],
                "last_active": user['last_active']
            }
            
        except Exception as e:
            logger.error(f"API error in get_user: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def api_spend_stars(self, request: Request):
        """API: Потратить звезды"""
        try:
            data = await request.json()
            user_id = data.get('user_id')
            amount = data.get('amount')
            
            if not user_id or not amount:
                raise HTTPException(status_code=400, detail="Missing user_id or amount")
            
            # Проверяем баланс
            user = await db.fetchone(
                "SELECT earned_stars FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not user or user['earned_stars'] < amount:
                raise HTTPException(status_code=400, detail="Not enough stars")
            
            # Обновляем баланс
            await db.execute('''
                UPDATE users 
                SET spent_stars = spent_stars + ?,
                    earned_stars = earned_stars - ?
                WHERE user_id = ?
            ''', (amount, amount, user_id))
            
            # Обновляем глобальный фонд
            await db.execute(
                "UPDATE global_fund SET total_stars = total_stars + ? WHERE id = 1",
                (amount,)
            )
            
            # Записываем транзакцию
            await db.execute('''
                INSERT INTO transactions (user_id, amount, type, description)
                VALUES (?, ?, 'api_spend', ?)
            ''', (user_id, amount, f"API spend: {amount} stars"))
            
            return {"success": True, "amount": amount}
            
        except Exception as e:
            logger.error(f"API error in spend_stars: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def api_get_leaderboard(self, limit: int = 10):
        """API: Получить таблицу лидеров"""
        try:
            users = await db.fetchall('''
                SELECT user_id, username, spent_stars, earned_stars 
                FROM users 
                WHERE is_banned = 0 
                ORDER BY spent_stars DESC 
                LIMIT ?
            ''', (limit,))
            
            return {
                "leaderboard": [
                    {
                        "position": i + 1,
                        "user_id": user['user_id'],
                        "username": user['username'] or f"User{user['user_id']}",
                        "spent_stars": user['spent_stars'],
                        "earned_stars": user['earned_stars']
                    }
                    for i, user in enumerate(users)
                ]
            }
            
        except Exception as e:
            logger.error(f"API error in get_leaderboard: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def start(self):
        """Запуск веб-сервера"""
        config = uvicorn.Config(
            self.app,
            host=Config.WEB_HOST,
            port=Config.WEB_PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# ============================================================================

async def main():
    """Главная функция запуска"""
    try:
        logger.info("=" * 60)
        logger.info("🖤 STARTING GOLDEN COBRA SUPREME v4.0 🖤")
        logger.info("=" * 60)
        
        # Создаем экземпляры
        bot = SupremeBot()
        web_app = SupremeWebApp(bot)
        
        # Запускаем в параллельных задачах
        await asyncio.gather(
            bot.start(),
            web_app.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise
    finally:
        logger.info("Golden Cobra Supreme shutdown complete")

if __name__ == "__main__":
    # Установка обработчика исключений
    import sys
    sys.excepthook = lambda exc_type, exc_value, exc_traceback: logger.critical(
        f"Uncaught exception: {exc_type.__name__}: {exc_value}"
    )
    
    # Запуск приложения
    asyncio.run(main())
