#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🖤 GOLDEN COBRA XTR TELEGRAM STARS v5.0 🖤
Полная интеграция реальных Telegram Stars (XTR)
Реальные платежи, реальная экономика, реальные вознаграждения
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
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass

# Telegram Bot с поддержкой Stars
from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, LabeledPrice, PreCheckoutQuery, SuccessfulPayment,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    ShippingOption, ShippingQuery, ShippingAddress,
    InputFile, Poll, PollAnswer, MenuButtonWebApp
)
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode, ContentType
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.methods import SetMyCommands, BotCommand

# Web Server
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ============================================================================
# КОНФИГУРАЦИЯ XTR TELEGRAM STARS
# ============================================================================

class XTRConfig:
    """Конфигурация для Telegram Stars"""
    
    # Основные настройки
    BOT_TOKEN = os.getenv('BOT_TOKEN', '8536282991:AAHUyTx0r7Q03bwDRokvogbmJAIbkAnYVpM')
    ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    
    # Настройки Stars
    STARS_CURRENCY = "XTR"
    STARS_PROVIDER_TOKEN = os.getenv('STARS_PROVIDER_TOKEN', '')  # Токен от @BotFather для платежей
    
    # Курс обмена (1 XTR = 1000 внутренних звезд)
    STARS_EXCHANGE_RATE = 1000
    
    # Минимальные/максимальные суммы
    MIN_STARS_PURCHASE = 10  # Минимальная покупка в XTR
    MAX_STARS_PURCHASE = 10000  # Максимальная покупка в XTR
    MIN_WITHDRAWAL = 100  # Минимальный вывод в XTR
    MAX_WITHDRAWAL = 5000  # Максимальный вывод в XTR
    
    # Комиссии
    PURCHASE_FEE_PERCENT = 0  # Комиссия при покупке (%)
    WITHDRAWAL_FEE_PERCENT = 5  # Комиссия при выводе (%)
    
    # База данных
    DB_FILE = os.getenv('DB_FILE', 'golden_cobra_xtr.db')
    
    # Веб-сервер
    WEB_PORT = int(os.getenv('WEB_PORT', 8000))
    WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
    
    # Папки
    BACKUP_DIR = 'backups'
    LOGS_DIR = 'logs'
    STATIC_DIR = 'static'
    CERTIFICATES_DIR = 'certificates'
    
    # Настройки безопасности
    PAYMENT_TIMEOUT = 300  # 5 минут на оплату
    MAX_PAYMENT_ATTEMPTS = 3
    ANTI_FRAUD_ENABLED = True
    
    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        if not cls.BOT_TOKEN or len(cls.BOT_TOKEN) < 10:
            raise ValueError("Invalid BOT_TOKEN")
        
        if not cls.STARS_PROVIDER_TOKEN:
            print("⚠️ Warning: STARS_PROVIDER_TOKEN not set. Payments will not work!")
        
        if not cls.ADMIN_IDS:
            cls.ADMIN_IDS = [123456789]
        
        # Создаем необходимые директории
        for directory in [cls.BACKUP_DIR, cls.LOGS_DIR, cls.STATIC_DIR, cls.CERTIFICATES_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        return True

# ============================================================================
# СИСТЕМА ЛОГИРОВАНИЯ
# ============================================================================

class XTRLogger:
    """Система логирования для XTR"""
    
    @staticmethod
    def setup():
        """Настройка логгера"""
        logger = logging.getLogger('GoldenCobraXTR')
        logger.setLevel(logging.INFO)
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Файловый вывод
        file_handler = logging.FileHandler(
            f'{XTRConfig.LOGS_DIR}/xtr_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

logger = XTRLogger.setup()

# ============================================================================
# БАЗА ДАННЫХ XTR - УЛУЧШЕННАЯ
# ============================================================================

class XTRDatabase:
    """База данных для XTR системы"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Инициализация базы данных"""
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA foreign_keys=ON")
                
                cursor = conn.cursor()
                
                # Пользователи
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        balance_stars INTEGER DEFAULT 0,  -- Внутренние звезды
                        balance_xtr INTEGER DEFAULT 0,    -- XTR баланс
                        total_deposited_xtr INTEGER DEFAULT 0,
                        total_withdrawn_xtr INTEGER DEFAULT 0,
                        referrals INTEGER DEFAULT 0,
                        referral_id INTEGER,
                        daily_streak INTEGER DEFAULT 0,
                        last_daily_claim TIMESTAMP,
                        language TEXT DEFAULT 'EN',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_verified BOOLEAN DEFAULT 0,
                        verification_level INTEGER DEFAULT 0,
                        is_banned BOOLEAN DEFAULT 0,
                        ban_reason TEXT,
                        UNIQUE(user_id)
                    )
                ''')
                
                # XTR транзакции
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS xtr_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        amount INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        provider_charge_id TEXT,
                        telegram_charge_id TEXT,
                        description TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        CHECK (type IN ('deposit', 'withdrawal', 'purchase', 'reward', 'commission')),
                        CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'))
                    )
                ''')
                
                # Внутренние транзакции
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS star_transactions (
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
                
                # Выводы XTR
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS withdrawals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        amount INTEGER NOT NULL,
                        fee INTEGER DEFAULT 0,
                        net_amount INTEGER NOT NULL,
                        status TEXT DEFAULT 'pending',
                        wallet_address TEXT,
                        transaction_hash TEXT,
                        admin_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        CHECK (status IN ('pending', 'processing', 'completed', 'rejected', 'cancelled'))
                    )
                ''')
                
                # NFT магазин
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS nft_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price_stars INTEGER NOT NULL,
                        price_xtr INTEGER,
                        rarity TEXT,
                        emoji TEXT,
                        image_url TEXT,
                        available BOOLEAN DEFAULT 1,
                        stock INTEGER DEFAULT -1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(name)
                    )
                ''')
                
                # NFT владение
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS nft_ownership (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        nft_id INTEGER NOT NULL,
                        purchase_price INTEGER,
                        purchase_type TEXT,
                        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_listed BOOLEAN DEFAULT 0,
                        listing_price INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (nft_id) REFERENCES nft_items(id),
                        UNIQUE(user_id, nft_id)
                    )
                ''')
                
                # NFT рынок
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS nft_market (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nft_ownership_id INTEGER NOT NULL,
                        seller_id INTEGER NOT NULL,
                        price_stars INTEGER,
                        price_xtr INTEGER,
                        listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sold_at TIMESTAMP,
                        buyer_id INTEGER,
                        FOREIGN KEY (nft_ownership_id) REFERENCES nft_ownership(id),
                        FOREIGN KEY (seller_id) REFERENCES users(user_id),
                        FOREIGN KEY (buyer_id) REFERENCES users(user_id)
                    )
                ''')
                
                # Реферальные выплаты
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS referral_payouts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referrer_id INTEGER NOT NULL,
                        referred_id INTEGER NOT NULL,
                        amount_xtr INTEGER NOT NULL,
                        percentage INTEGER DEFAULT 10,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        paid_at TIMESTAMP,
                        FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                        FOREIGN KEY (referred_id) REFERENCES users(user_id)
                    )
                ''')
                
                # Курсы обмена
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS exchange_rates (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        stars_per_xtr INTEGER DEFAULT 1000,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Вставляем начальные данные
                self._insert_initial_data(cursor)
                
                conn.commit()
                logger.info("База данных XTR инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    def _insert_initial_data(self, cursor):
        """Вставка начальных данных"""
        try:
            # Курс обмена
            cursor.execute('''
                INSERT OR IGNORE INTO exchange_rates (id, stars_per_xtr)
                VALUES (1, 1000)
            ''')
            
            # NFT предметы
            nft_items = [
                ('Golden Cobra Crown', 'Корона золотой кобры', 10000, 10, 'Legendary', '👑', None),
                ('Blood Viper NFT', 'Кровавая гадюка NFT', 5000, 5, 'Epic', '🩸', None),
                ('Skull Cobra', 'Череп кобры', 1000, 1, 'Rare', '💀', None),
                ('Diamond Scale', 'Алмазная чешуя', 7500, 7.5, 'Epic', '💎', None),
                ('Shadow Serpent', 'Теневой змей', 2500, 2.5, 'Rare', '🌑', None),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO nft_items 
                (name, description, price_stars, price_xtr, rarity, emoji, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', nft_items)
            
        except Exception as e:
            logger.error(f"Ошибка вставки начальных данных: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Асинхронное соединение с БД"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    async def execute(self, query: str, params: tuple = None):
        """Выполнить запрос"""
        async with self.get_connection() as db:
            await db.execute(query, params or ())
            await db.commit()
    
    async def fetchone(self, query: str, params: tuple = None):
        """Получить одну запись"""
        async with self.get_connection() as db:
            async with db.execute(query, params or ()) as cursor:
                return await cursor.fetchone()
    
    async def fetchall(self, query: str, params: tuple = None):
        """Получить все записи"""
        async with self.get_connection() as db:
            async with db.execute(query, params or ()) as cursor:
                return await cursor.fetchall()
    
    async def backup(self):
        """Создать резервную копию"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{XTRConfig.BACKUP_DIR}/xtr_backup_{timestamp}.db"
            
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
    XTRConfig.validate()
    db = XTRDatabase(XTRConfig.DB_FILE)
    logger.info("Конфигурация XTR загружена успешно")
except Exception as e:
    logger.critical(f"Критическая ошибка инициализации: {e}")
    sys.exit(1)

# ============================================================================
# СИСТЕМА XTR ПЛАТЕЖЕЙ
# ============================================================================

class XTRPaymentSystem:
    """Система обработки Telegram Stars платежей"""
    
    @staticmethod
    async def create_invoice_link(
        bot: Bot,
        chat_id: int,
        amount_xtr: int,
        description: str,
        payload: str,
        **kwargs
    ) -> str:
        """Создать ссылку на оплату"""
        try:
            if not XTRConfig.STARS_PROVIDER_TOKEN:
                raise ValueError("STARS_PROVIDER_TOKEN not configured")
            
            prices = [LabeledPrice(label=description, amount=amount_xtr)]
            
            result = await bot.send_invoice(
                chat_id=chat_id,
                title="Golden Cobra XTR Payment",
                description=description,
                payload=payload,
                provider_token=XTRConfig.STARS_PROVIDER_TOKEN,
                currency=XTRConfig.STARS_CURRENCY,
                prices=prices,
                **kwargs
            )
            
            return result.url if hasattr(result, 'url') else None
            
        except Exception as e:
            logger.error(f"Ошибка создания инвойса: {e}")
            return None
    
    @staticmethod
    async def process_deposit(
        user_id: int,
        amount_xtr: int,
        provider_charge_id: str,
        telegram_charge_id: str
    ) -> bool:
        """Обработать депозит XTR"""
        try:
            # Конвертируем XTR во внутренние звезды
            exchange_rate = await db.fetchone(
                "SELECT stars_per_xtr FROM exchange_rates WHERE id = 1"
            )
            stars_per_xtr = exchange_rate['stars_per_xtr'] if exchange_rate else 1000
            
            stars_amount = amount_xtr * stars_per_xtr
            
            # Начинаем транзакцию
            async with db.get_connection() as conn:
                # Обновляем баланс пользователя
                await conn.execute('''
                    UPDATE users 
                    SET balance_xtr = balance_xtr + ?,
                        balance_stars = balance_stars + ?,
                        total_deposited_xtr = total_deposited_xtr + ?
                    WHERE user_id = ?
                ''', (amount_xtr, stars_amount, amount_xtr, user_id))
                
                # Записываем XTR транзакцию
                await conn.execute('''
                    INSERT INTO xtr_transactions 
                    (user_id, amount, type, status, provider_charge_id, telegram_charge_id, description, completed_at)
                    VALUES (?, ?, 'deposit', 'completed', ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, amount_xtr, provider_charge_id, telegram_charge_id, 
                      f"Deposit {amount_xtr} XTR"))
                
                # Записываем звездную транзакцию
                await conn.execute('''
                    INSERT INTO star_transactions 
                    (user_id, amount, type, description)
                    VALUES (?, ?, 'deposit', ?)
                ''', (user_id, stars_amount, f"Deposit from {amount_xtr} XTR"))
                
                await conn.commit()
            
            logger.info(f"Депозит обработан: user={user_id}, xtr={amount_xtr}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки депозита: {e}")
            return False
    
    @staticmethod
    async def process_withdrawal(
        user_id: int,
        amount_xtr: int,
        wallet_address: str
    ) -> Tuple[bool, str]:
        """Обработать вывод XTR"""
        try:
            # Проверяем баланс
            user = await db.fetchone(
                "SELECT balance_xtr, is_verified FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not user:
                return False, "Пользователь не найден"
            
            if user['balance_xtr'] < amount_xtr:
                return False, "Недостаточно XTR на балансе"
            
            if amount_xtr < XTRConfig.MIN_WITHDRAWAL:
                return False, f"Минимальная сумма вывода: {XTRConfig.MIN_WITHDRAWAL} XTR"
            
            if amount_xtr > XTRConfig.MAX_WITHDRAWAL:
                return False, f"Максимальная сумма вывода: {XTRConfig.MAX_WITHDRAWAL} XTR"
            
            if not user['is_verified'] and amount_xtr > 500:
                return False, "Требуется верификация для вывода > 500 XTR"
            
            # Рассчитываем комиссию
            fee = int(amount_xtr * XTRConfig.WITHDRAWAL_FEE_PERCENT / 100)
            net_amount = amount_xtr - fee
            
            # Создаем запрос на вывод
            withdrawal_id = await db.execute('''
                INSERT INTO withdrawals 
                (user_id, amount, fee, net_amount, status, wallet_address)
                VALUES (?, ?, ?, ?, 'pending', ?)
            ''', (user_id, amount_xtr, fee, net_amount, wallet_address))
            
            # Резервируем средства
            await db.execute(
                "UPDATE users SET balance_xtr = balance_xtr - ? WHERE user_id = ?",
                (amount_xtr, user_id)
            )
            
            return True, f"Заявка на вывод создана: {net_amount} XTR (комиссия: {fee} XTR)"
            
        except Exception as e:
            logger.error(f"Ошибка обработки вывода: {e}")
            return False, f"Ошибка: {str(e)}"
    
    @staticmethod
    async def process_nft_purchase(
        user_id: int,
        nft_id: int,
        payment_type: str,  # 'stars' или 'xtr'
        amount: int
    ) -> Tuple[bool, str, Optional[int]]:
        """Обработать покупку NFT"""
        try:
            # Получаем информацию о NFT
            nft = await db.fetchone(
                "SELECT * FROM nft_items WHERE id = ? AND available = 1",
                (nft_id,)
            )
            
            if not nft:
                return False, "NFT не найден или недоступен", None
            
            if payment_type == 'stars':
                price = nft['price_stars']
                user_balance_field = 'balance_stars'
            elif payment_type == 'xtr':
                price = nft['price_xtr']
                user_balance_field = 'balance_xtr'
            else:
                return False, "Неверный тип оплаты", None
            
            if amount < price:
                return False, f"Недостаточно средств. Цена: {price}", None
            
            # Проверяем баланс
            user = await db.fetchone(
                f"SELECT {user_balance_field} FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not user or user[user_balance_field] < amount:
                return False, "Недостаточно средств", None
            
            # Проверяем сток
            if nft['stock'] == 0:
                return False, "Товар закончился", None
            
            # Начинаем транзакцию
            async with db.get_connection() as conn:
                # Списание средств
                await conn.execute(f'''
                    UPDATE users SET {user_balance_field} = {user_balance_field} - ? 
                    WHERE user_id = ?
                ''', (amount, user_id))
                
                # Запись транзакции
                if payment_type == 'stars':
                    await conn.execute('''
                        INSERT INTO star_transactions 
                        (user_id, amount, type, description)
                        VALUES (?, ?, 'purchase', ?)
                    ''', (user_id, -amount, f"Покупка NFT: {nft['name']}"))
                else:
                    await conn.execute('''
                        INSERT INTO xtr_transactions 
                        (user_id, amount, type, status, description, completed_at)
                        VALUES (?, ?, 'purchase', 'completed', ?, CURRENT_TIMESTAMP)
                    ''', (user_id, -amount, f"Покупка NFT: {nft['name']}"))
                
                # Создание владения NFT
                await conn.execute('''
                    INSERT INTO nft_ownership 
                    (user_id, nft_id, purchase_price, purchase_type)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, nft_id, amount, payment_type))
                
                # Обновление стока
                if nft['stock'] > 0:
                    await conn.execute(
                        "UPDATE nft_items SET stock = stock - 1 WHERE id = ?",
                        (nft_id,)
                    )
                
                await conn.commit()
            
            # Получаем ID владения
            ownership = await db.fetchone(
                "SELECT id FROM nft_ownership WHERE user_id = ? AND nft_id = ? ORDER BY id DESC LIMIT 1",
                (user_id, nft_id)
            )
            
            return True, f"NFT '{nft['name']}' успешно куплен!", ownership['id'] if ownership else None
            
        except Exception as e:
            logger.error(f"Ошибка покупки NFT: {e}")
            return False, f"Ошибка: {str(e)}", None

# ============================================================================
# ОСНОВНОЙ БОТ XTR
# ============================================================================

class XTRBot:
    """Основной бот с поддержкой XTR"""
    
    def __init__(self):
        self.bot = Bot(
            token=XTRConfig.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.router = Router()
        self.dp.include_router(self.router)
        
        # Система платежей
        self.payment_system = XTRPaymentSystem()
        
        # Состояния FSM
        class States(StatesGroup):
            awaiting_deposit_amount = State()
            awaiting_withdrawal_amount = State()
            awaiting_withdrawal_wallet = State()
            awaiting_nft_purchase = State()
            awaiting_payment_confirmation = State()
        
        self.states = States()
        
        # Регистрация обработчиков
        self.register_handlers()
        
        logger.info("XTR Bot initialized")
    
    def register_handlers(self):
        """Регистрация всех обработчиков"""
        
        @self.router.message(Command("start"))
        async def cmd_start(message: Message, command: CommandObject = None):
            await self.handle_start(message, command)
        
        @self.router.message(Command("deposit"))
        async def cmd_deposit(message: Message, command: CommandObject = None):
            await self.handle_deposit(message, command)
        
        @self.router.message(Command("withdraw"))
        async def cmd_withdraw(message: Message, command: CommandObject = None):
            await self.handle_withdraw(message, command)
        
        @self.router.message(Command("balance"))
        async def cmd_balance(message: Message):
            await self.handle_balance(message)
        
        @self.router.message(Command("buy_stars"))
        async def cmd_buy_stars(message: Message, command: CommandObject = None):
            await self.handle_buy_stars(message, command)
        
        @self.router.message(Command("nft_shop"))
        async def cmd_nft_shop(message: Message):
            await self.handle_nft_shop(message)
        
        @self.router.message(Command("my_nfts"))
        async def cmd_my_nfts(message: Message):
            await self.handle_my_nfts(message)
        
        @self.router.message(Command("exchange"))
        async def cmd_exchange(message: Message, command: CommandObject = None):
            await self.handle_exchange(message, command)
        
        @self.router.message(Command("help"))
        async def cmd_help(message: Message):
            await self.handle_help(message)
        
        @self.router.message(Command("admin"))
        async def cmd_admin(message: Message, command: CommandObject = None):
            await self.handle_admin(message, command)
        
        # Обработчики платежей
        @self.router.pre_checkout_query()
        async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
            await self.handle_pre_checkout(pre_checkout_query)
        
        @self.router.message(F.successful_payment)
        async def successful_payment_handler(message: Message):
            await self.handle_successful_payment(message)
        
        # Callback обработчики
        @self.router.callback_query(F.data.startswith("deposit_"))
        async def deposit_callback(callback: CallbackQuery):
            await self.handle_deposit_callback(callback)
        
        @self.router.callback_query(F.data.startswith("nft_"))
        async def nft_callback(callback: CallbackQuery):
            await self.handle_nft_callback(callback)
        
        @self.router.callback_query(F.data.startswith("withdraw_"))
        async def withdraw_callback(callback: CallbackQuery):
            await self.handle_withdraw_callback(callback)
    
    async def handle_start(self, message: Message, command: CommandObject):
        """Обработка команды /start"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name
            
            # Создаем/обновляем пользователя
            await db.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_active) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, message.from_user.first_name))
            
            # Приветственное сообщение
            welcome_text = """
🖤 **GOLDEN COBRA XTR EDITION** 🖤

*Добро пожаловать в мир реальных Telegram Stars (XTR)!*

💰 **Основные возможности:**
• Пополнение баланса реальными XTR
• Вывод заработанных XTR на кошелек
• Покупка NFT за реальные деньги
• Торговля на внутреннем рынке
• Реферальная программа с выплатами в XTR

💎 **Быстрый старт:**
1. /deposit - Пополнить баланс XTR
2. /balance - Проверить баланс
3. /nft_shop - Магазин NFT
4. /withdraw - Вывести XTR

🚀 **Начните зарабатывать реальные деньги уже сегодня!**
            """
            
            # Клавиатура
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="💰 Пополнить баланс", callback_data="deposit_menu")
            keyboard.button(text="🏪 NFT Магазин", callback_data="nft_shop_menu")
            keyboard.button(text="💎 Мой баланс", callback_data="balance_menu")
            keyboard.button(text="📊 Таблица лидеров", callback_data="leaderboard_menu")
            keyboard.adjust(2)
            
            await message.answer(welcome_text, reply_markup=keyboard.as_markup())
            
        except Exception as e:
            logger.error(f"Ошибка в handle_start: {e}")
            await message.answer("❌ Ошибка инициализации профиля")
    
    async def handle_deposit(self, message: Message, command: CommandObject):
        """Обработка команды /deposit"""
        try:
            if command and command.args:
                try:
                    amount = int(command.args)
                    
                    if amount < XTRConfig.MIN_STARS_PURCHASE:
                        await message.answer(
                            f"❌ Минимальная сумма пополнения: {XTRConfig.MIN_STARS_PURCHASE} XTR"
                        )
                        return
                    
                    if amount > XTRConfig.MAX_STARS_PURCHASE:
                        await message.answer(
                            f"❌ Максимальная сумма пополнения: {XTRConfig.MAX_STARS_PURCHASE} XTR"
                        )
                        return
                    
                    # Создаем инвойс
                    payload = f"deposit_{message.from_user.id}_{amount}_{int(time.time())}"
                    
                    invoice_url = await self.payment_system.create_invoice_link(
                        bot=self.bot,
                        chat_id=message.chat.id,
                        amount_xtr=amount,
                        description=f"Пополнение баланса на {amount} XTR",
                        payload=payload,
                        start_parameter="deposit"
                    )
                    
                    if invoice_url:
                        keyboard = InlineKeyboardBuilder()
                        keyboard.button(text="💳 Оплатить", url=invoice_url)
                        keyboard.button(text="🔄 Проверить оплату", callback_data=f"check_deposit_{payload}")
                        
                        await message.answer(
                            f"💎 **Пополнение баланса**\n\n"
                            f"Сумма: {amount} XTR\n"
                            f"Курс: 1 XTR = 1000 внутренних звезд\n"
                            f"Вы получите: {amount * 1000} ⭐\n\n"
                            f"*Нажмите кнопку ниже для оплаты:*",
                            reply_markup=keyboard.as_markup()
                        )
                    else:
                        await message.answer("❌ Ошибка создания платежа")
                        
                except ValueError:
                    await message.answer("❌ Неверная сумма. Использование: /deposit <amount>")
            else:
                # Показываем меню пополнения
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="💎 10 XTR (10,000 ⭐)", callback_data="deposit_10")
                keyboard.button(text="💎 50 XTR (50,000 ⭐)", callback_data="deposit_50")
                keyboard.button(text="💎 100 XTR (100,000 ⭐)", callback_data="deposit_100")
                keyboard.button(text="💎 500 XTR (500,000 ⭐)", callback_data="deposit_500")
                keyboard.button(text="💎 Другая сумма", callback_data="deposit_custom")
                keyboard.adjust(2)
                
                await message.answer(
                    "💎 **Выберите сумму для пополнения:**\n\n"
                    "1 XTR = 1000 внутренних звезд\n\n"
                    "*Доступные варианты:*",
                    reply_markup=keyboard.as_markup()
                )
                
        except Exception as e:
            logger.error(f"Ошибка в handle_deposit: {e}")
            await message.answer("❌ Ошибка обработки запроса")
    
    async def handle_withdraw(self, message: Message, command: CommandObject):
        """Обработка команды /withdraw"""
        try:
            user_id = message.from_user.id
            
            # Получаем баланс
            user = await db.fetchone(
                "SELECT balance_xtr, is_verified FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not user:
                await message.answer("❌ Пользователь не найден")
                return
            
            if command and command.args:
                try:
                    args = command.args.split()
                    if len(args) < 2:
                        await message.answer("❌ Использование: /withdraw <amount> <wallet_address>")
                        return
                    
                    amount = int(args[0])
                    wallet_address = args[1]
                    
                    # Обрабатываем вывод
                    success, result = await self.payment_system.process_withdrawal(
                        user_id, amount, wallet_address
                    )
                    
                    if success:
                        await message.answer(f"✅ {result}")
                        
                        # Уведомляем админов
                        for admin_id in XTRConfig.ADMIN_IDS:
                            try:
                                await self.bot.send_message(
                                    admin_id,
                                    f"🔄 **НОВЫЙ ВЫВОД**\n\n"
                                    f"👤 Пользователь: @{message.from_user.username or user_id}\n"
                                    f"💰 Сумма: {amount} XTR\n"
                                    f"🎯 Кошелек: {wallet_address}\n"
                                    f"🆔 ID: {user_id}"
                                )
                            except:
                                pass
                    else:
                        await message.answer(f"❌ {result}")
                        
                except ValueError:
                    await message.answer("❌ Неверная сумма")
                except Exception as e:
                    await message.answer(f"❌ Ошибка: {str(e)}")
            else:
                # Показываем информацию о выводе
                withdrawal_info = f"""
💸 **Вывод XTR**

💰 Ваш баланс: {user['balance_xtr']} XTR
✅ Статус верификации: {'Пройдена' if user['is_verified'] else 'Требуется'}

📊 **Условия вывода:**
• Минимум: {XTRConfig.MIN_WITHDRAWAL} XTR
• Максимум: {XTRConfig.MAX_WITHDRAWAL} XTR
• Комиссия: {XTRConfig.WITHDRAWAL_FEE_PERCENT}%

⚠️ **Для вывода > 500 XTR требуется верификация**

📝 **Использование:**
`/withdraw <amount> <wallet_address>`

Пример: `/withdraw 100 UQB...`
                """
                
                keyboard = InlineKeyboardBuilder()
                if not user['is_verified']:
                    keyboard.button(text="✅ Пройти верификацию", callback_data="verify_request")
                keyboard.button(text="📋 Мои заявки", callback_data="withdraw_requests")
                keyboard.adjust(1)
                
                await message.answer(withdrawal_info, reply_markup=keyboard.as_markup())
                
        except Exception as e:
            logger.error(f"Ошибка в handle_withdraw: {e}")
            await message.answer("❌ Ошибка обработки запроса")
    
    async def handle_balance(self, message: Message):
        """Обработка команды /balance"""
        try:
            user_id = message.from_user.id
            
            # Получаем данные пользователя
            user = await db.fetchone('''
                SELECT balance_stars, balance_xtr, total_deposited_xtr, 
                       total_withdrawn_xtr, referrals, is_verified
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            if not user:
                await message.answer("❌ Пользователь не найден")
                return
            
            # Получаем курс
            exchange = await db.fetchone("SELECT stars_per_xtr FROM exchange_rates WHERE id = 1")
            stars_per_xtr = exchange['stars_per_xtr'] if exchange else 1000
            
            # Получаем последние транзакции
            last_xtr = await db.fetchall('''
                SELECT * FROM xtr_transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            ''', (user_id,))
            
            # Формируем сообщение
            balance_text = f"""
💰 **ВАШ БАЛАНС**

💎 **Telegram Stars (XTR):**
• Доступно: {user['balance_xtr']} XTR
• Всего пополнено: {user['total_deposited_xtr']} XTR
• Всего выведено: {user['total_withdrawn_xtr']} XTR

⭐ **Внутренние звезды:**
• Баланс: {user['balance_stars']} ⭐
• Курс: 1 XTR = {stars_per_xtr} ⭐

👥 **Рефералы:**
• Приглашено: {user['referrals']} пользователей
• Статус: {'✅ Верифицирован' if user['is_verified'] else '❌ Требуется верификация'}

💸 **Примерная стоимость:**
• Ваш баланс в XTR: ≈${user['balance_xtr'] * 0.01:.2f} USD
            """
            
            if last_xtr:
                balance_text += "\n\n📊 **Последние транзакции:**\n"
                for tx in last_xtr:
                    emoji = "⬆️" if tx['type'] == 'deposit' else "⬇️"
                    balance_text += f"{emoji} {tx['type']}: {tx['amount']} XTR\n"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="💰 Пополнить", callback_data="deposit_menu")
            keyboard.button(text="💸 Вывести", callback_data="withdraw_menu")
            keyboard.button(text="📊 Подробная статистика", callback_data="stats_detailed")
            keyboard.adjust(2)
            
            await message.answer(balance_text, reply_markup=keyboard.as_markup())
            
        except Exception as e:
            logger.error(f"Ошибка в handle_balance: {e}")
            await message.answer("❌ Ошибка получения баланса")
    
    async def handle_buy_stars(self, message: Message, command: CommandObject):
        """Обработка команды /buy_stars"""
        try:
            if command and command.args:
                try:
                    amount = int(command.args)
                    
                    if amount < 1000:
                        await message.answer("❌ Минимум 1000 звезд")
                        return
                    
                    # Рассчитываем стоимость в XTR
                    exchange = await db.fetchone("SELECT stars_per_xtr FROM exchange_rates WHERE id = 1")
                    stars_per_xtr = exchange['stars_per_xtr'] if exchange else 1000
                    
                    xtr_amount = amount // stars_per_xtr
                    if amount % stars_per_xtr != 0:
                        xtr_amount += 1
                    
                    if xtr_amount < XTRConfig.MIN_STARS_PURCHASE:
                        xtr_amount = XTRConfig.MIN_STARS_PURCHASE
                    
                    # Создаем инвойс
                    payload = f"buy_stars_{message.from_user.id}_{amount}_{xtr_amount}"
                    
                    invoice_url = await self.payment_system.create_invoice_link(
                        bot=self.bot,
                        chat_id=message.chat.id,
                        amount_xtr=xtr_amount,
                        description=f"Покупка {amount} звезд",
                        payload=payload,
                        start_parameter="buy_stars"
                    )
                    
                    if invoice_url:
                        keyboard = InlineKeyboardBuilder()
                        keyboard.button(text="💳 Купить", url=invoice_url)
                        
                        await message.answer(
                            f"⭐ **Покупка звезд**\n\n"
                            f"Количество: {amount} ⭐\n"
                            f"Стоимость: {xtr_amount} XTR\n"
                            f"Курс: 1 XTR = {stars_per_xtr} ⭐\n\n"
                            f"*Нажмите кнопку для оплаты:*",
                            reply_markup=keyboard.as_markup()
                        )
                    else:
                        await message.answer("❌ Ошибка создания платежа")
                        
                except ValueError:
                    await message.answer("❌ Неверная сумма. Использование: /buy_stars <amount>")
            else:
                await message.answer(
                    "⭐ **Покупка внутренних звезд**\n\n"
                    "Используйте: `/buy_stars <amount>`\n"
                    "Пример: `/buy_stars 10000`\n\n"
                    "Минимум: 1000 звезд\n"
                    "Курс: 1 XTR = 1000 ⭐"
                )
                
        except Exception as e:
            logger.error(f"Ошибка в handle_buy_stars: {e}")
            await message.answer("❌ Ошибка обработки запроса")
    
    async def handle_nft_shop(self, message: Message):
        """Обработка команды /nft_shop"""
        try:
            # Получаем NFT из магазина
            nfts = await db.fetchall('''
                SELECT * FROM nft_items 
                WHERE available = 1 
                ORDER BY price_xtr ASC
            ''')
            
            if not nfts:
                await message.answer("🛒 Магазин NFT пуст!")
                return
            
            # Создаем карусель NFT
            keyboard = InlineKeyboardBuilder()
            
            shop_text = "🛒 **NFT МАГАЗИН** 🛒\n\n"
            
            for nft in nfts:
                stock_info = f" ({nft['stock']} шт.)" if nft['stock'] > 0 else " (∞)"
                shop_text += f"{nft['emoji']} **{nft['name']}**\n"
                shop_text += f"*{nft['description']}*\n"
                shop_text += f"💰 Цена: {nft['price_xtr']} XTR или {nft['price_stars']} ⭐\n"
                shop_text += f"🎯 Редкость: {nft['rarity']}{stock_info}\n"
                shop_text += f"🆔 ID: `{nft['id']}`\n\n"
                
                # Кнопки для покупки
                keyboard.button(
                    text=f"{nft['emoji']} Купить за {nft['price_xtr']}XTR",
                    callback_data=f"nft_buy_xtr_{nft['id']}"
                )
                keyboard.button(
                    text=f"{nft['emoji']} Купить за {nft['price_stars']}⭐",
                    callback_data=f"nft_buy_stars_{nft['id']}"
                )
            
            keyboard.adjust(1)
            shop_text += "\n*Выберите способ оплаты для покупки NFT*"
            
            await message.answer(shop_text, reply_markup=keyboard.as_markup())
            
        except Exception as e:
            logger.error(f"Ошибка в handle_nft_shop: {e}")
            await message.answer("❌ Ошибка загрузки магазина")
    
    async def handle_my_nfts(self, message: Message):
        """Обработка команды /my_nfts"""
        try:
            user_id = message.from_user.id
            
            # Получаем NFT пользователя
            nfts = await db.fetchall('''
                SELECT no.*, ni.name, ni.description, ni.rarity, ni.emoji
                FROM nft_ownership no
                JOIN nft_items ni ON no.nft_id = ni.id
                WHERE no.user_id = ?
                ORDER BY no.purchased_at DESC
            ''', (user_id,))
            
            if not nfts:
                await message.answer(
                    "🎒 **Ваша коллекция NFT пуста!**\n\n"
                    "Посетите магазин: /nft_shop\n"
                    "Купите свой первый NFT за XTR или внутренние звезды!"
                )
                return
            
            # Формируем сообщение
            nfts_text = f"🎒 **ВАША КОЛЛЕКЦИЯ NFT** ({len(nfts)} шт.)\n\n"
            
            total_value_xtr = 0
            total_value_stars = 0
            
            for nft in nfts:
                nfts_text += f"{nft['emoji']} **{nft['name']}**\n"
                nfts_text += f"*{nft['description']}*\n"
                nfts_text += f"🎯 Редкость: {nft['rarity']}\n"
                nfts_text += f"💰 Куплено за: {nft['purchase_price']} {nft['purchase_type']}\n"
                nfts_text += f"📅 Дата: {nft['purchased_at'][:10]}\n\n"
                
                if nft['purchase_type'] == 'xtr':
                    total_value_xtr += nft['purchase_price']
                else:
                    total_value_stars += nft['purchase_price']
            
            nfts_text += f"💎 **Общая стоимость:**\n"
            nfts_text += f"• В XTR: {total_value_xtr} XTR\n"
            nfts_text += f"• В звездах: {total_value_stars} ⭐\n\n"
            nfts_text += f"💸 **Примерная стоимость:** ${total_value_xtr * 0.01:.2f} USD"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🛒 Магазин NFT", callback_data="nft_shop_menu")
            keyboard.button(text="📊 Продать NFT", callback_data="nft_sell_menu")
            keyboard.button(text="🎯 Торговая площадка", callback_data="nft_marketplace")
            keyboard.adjust(2)
            
            await message.answer(nfts_text, reply_markup=keyboard.as_markup())
            
        except Exception as e:
            logger.error(f"Ошибка в handle_my_nfts: {e}")
            await message.answer("❌ Ошибка загрузки коллекции")
    
    async def handle_exchange(self, message: Message, command: CommandObject):
        """Обработка команды /exchange"""
        try:
            if command and command.args:
                try:
                    args = command.args.split()
                    if len(args) != 2:
                        await message.answer("❌ Использование: /exchange <amount> <from> <to>\nПример: /exchange 100 stars xtr")
                        return
                    
                    amount = float(args[0])
                    from_currency = args[1].lower()
                    
                    # Получаем курс
                    exchange = await db.fetchone("SELECT stars_per_xtr FROM exchange_rates WHERE id = 1")
                    stars_per_xtr = exchange['stars_per_xtr'] if exchange else 1000
                    
                    if from_currency in ['stars', '⭐']:
                        # Конвертация звезд в XTR
                        xtr_amount = amount / stars_per_xtr
                        await message.answer(
                            f"💱 **Конвертация**\n\n"
                            f"Из: {amount} ⭐\n"
                            f"В: {xtr_amount:.2f} XTR\n"
                            f"Курс: 1 XTR = {stars_per_xtr} ⭐\n\n"
                            f"*Для конвертации используйте команду:*\n"
                            f"`/deposit` - купить XTR за деньги\n"
                            f"`/withdraw` - вывести XTR"
                        )
                    elif from_currency in ['xtr', 'x']:
                        # Конвертация XTR в звезды
                        stars_amount = amount * stars_per_xtr
                        await message.answer(
                            f"💱 **Конвертация**\n\n"
                            f"Из: {amount} XTR\n"
                            f"В: {stars_amount} ⭐\n"
                            f"Курс: 1 XTR = {stars_per_xtr} ⭐\n\n"
                            f"*Для получения XTR используйте:*\n"
                            f"`/deposit` - пополнить баланс"
                        )
                    else:
                        await message.answer("❌ Неверная валюта. Используйте 'stars' или 'xtr'")
                        
                except ValueError:
                    await message.answer("❌ Неверная сумма")
            else:
                # Показываем информацию об обмене
                exchange = await db.fetchone("SELECT stars_per_xtr FROM exchange_rates WHERE id = 1")
                stars_per_xtr = exchange['stars_per_xtr'] if exchange else 1000
                
                exchange_text = f"""
💱 **ОБМЕННЫЙ КУРС**

💰 **Текущий курс:**
• 1 XTR = {stars_per_xtr} ⭐
• 1000 ⭐ = {1000/stars_per_xtr:.2f} XTR

💎 **Стоимость XTR:**
• 1 XTR ≈ $0.01 USD
• 100 XTR ≈ $1.00 USD

📊 **Как это работает:**
1. Покупаете XTR через /deposit
2. Конвертируете в звезды автоматически
3. Тратите звезды в магазине
4. Заработанные XTR выводите через /withdraw

🔄 **Конвертация:**
• `/exchange 1000 stars xtr` - сколько XTR за 1000 звезд
• `/exchange 10 xtr stars` - сколько звезд за 10 XTR
                """
                
                await message.answer(exchange_text)
                
        except Exception as e:
            logger.error(f"Ошибка в handle_exchange: {e}")
            await message.answer("❌ Ошибка обработки запроса")
    
    async def handle_help(self, message: Message):
        """Обработка команды /help"""
        help_text = """
🖤 **GOLDEN COBRA XTR - ПОМОЩЬ** 🖤

*Основные команды:*
/start - Начало работы
/balance - Ваш баланс
/deposit - Пополнить XTR
/withdraw - Вывести XTR
/exchange - Курс обмена

*NFT система:*
/nft_shop - Магазин NFT
/my_nfts - Ваша коллекция
/buy_stars - Купить звезды

*Администрация:*
/admin - Панель администратора
/admin stats - Статистика
/admin users - Управление пользователями
/admin verify <id> - Верификация

*Поддержка:*
Для вопросов по платежам, выводам или техническим проблемам обращайтесь к администратору.

💎 **Помните:** 
• 1 XTR = 1000 внутренних звезд
• XTR можно выводить на кошелек
• Минимальный вывод: 100 XTR
• Комиссия на вывод: 5%
        """
        
        await message.answer(help_text)
    
    async def handle_admin(self, message: Message, command: CommandObject):
        """Обработка команды /admin"""
        try:
            user_id = message.from_user.id
            
            if user_id not in XTRConfig.ADMIN_IDS:
                await message.answer("❌ Доступ запрещен!")
                return
            
            if not command or not command.args:
                admin_text = """
🛡️ **АДМИН ПАНЕЛЬ XTR** 🛡️

*Основные команды:*
/admin stats - Статистика системы
/admin backup - Создать бэкап
/admin users - Список пользователей
/admin user <id> - Инфо о пользователе
/admin verify <id> - Верифицировать
/admin ban <id> <reason> - Заблокировать

*Финансы:*
/admin deposits - Депозиты
/admin withdrawals - Заявки на вывод
/admin approve <id> - Одобрить вывод
/admin reject <id> <reason> - Отклонить вывод
/admin addxtr <id> <amount> - Добавить XTR

*NFT:*
/admin nfts - Управление NFT
/admin addnft - Добавить NFT
                """
                await message.answer(admin_text)
                return
            
            args = command.args.split()
            cmd = args[0].lower()
            
            if cmd == "stats":
                await self.handle_admin_stats(message)
            elif cmd == "backup":
                await self.handle_admin_backup(message)
            elif cmd == "users":
                await self.handle_admin_users(message, args[1:] if len(args) > 1 else [])
            elif cmd == "verify":
                if len(args) < 2:
                    await message.answer("Использование: /admin verify <user_id>")
                    return
                await self.handle_admin_verify(message, args[1])
            elif cmd == "withdrawals":
                await self.handle_admin_withdrawals(message)
            elif cmd == "approve":
                if len(args) < 2:
                    await message.answer("Использование: /admin approve <withdrawal_id>")
                    return
                await self.handle_admin_approve(message, args[1])
            else:
                await message.answer("❌ Неизвестная команда")
                
        except Exception as e:
            logger.error(f"Ошибка в handle_admin: {e}")
            await message.answer("❌ Ошибка выполнения команды")
    
    async def handle_admin_stats(self, message: Message):
        """Статистика системы"""
        try:
            # Общая статистика
            total_users = await db.fetchone("SELECT COUNT(*) as count FROM users")
            active_users = await db.fetchone('''
                SELECT COUNT(*) as count FROM users 
                WHERE datetime(last_active) > datetime('now', '-7 days')
            ''')
            
            total_deposits = await db.fetchone("SELECT SUM(amount) as total FROM xtr_transactions WHERE type = 'deposit'")
            total_withdrawals = await db.fetchone("SELECT SUM(amount) as total FROM xtr_transactions WHERE type = 'withdrawal'")
            
            # Балансы системы
            system_balance = await db.fetchone("SELECT SUM(balance_xtr) as total FROM users")
            
            # NFT статистика
            nft_sales = await db.fetchone("SELECT COUNT(*) as count FROM nft_ownership")
            
            stats_text = f"""
📊 **СТАТИСТИКА СИСТЕМЫ XTR**

👥 **Пользователи:**
• Всего: {total_users['count'] if total_users else 0}
• Активных (7 дней): {active_users['count'] if active_users else 0}

💰 **Финансы:**
• Всего депозитов: {total_deposits['total'] or 0} XTR
• Всего выводов: {total_withdrawals['total'] or 0} XTR
• Баланс системы: {system_balance['total'] or 0} XTR

🎨 **NFT:**
• Продано NFT: {nft_sales['count'] if nft_sales else 0}

💸 **В ожидании:**
• Заявок на вывод: {await self.get_pending_withdrawals_count()}
            """
            
            await message.answer(stats_text)
            
        except Exception as e:
            logger.error(f"Ошибка в handle_admin_stats: {e}")
            await message.answer("❌ Ошибка получения статистики")
    
    async def handle_admin_backup(self, message: Message):
        """Создание бэкапа"""
        try:
            backup_path = await db.backup()
            if backup_path:
                await message.answer(f"✅ Бэкап создан: `{backup_path}`")
            else:
                await message.answer("❌ Ошибка создания бэкапа")
        except Exception as e:
            logger.error(f"Ошибка в handle_admin_backup: {e}")
            await message.answer("❌ Ошибка создания бэкапа")
    
    async def get_pending_withdrawals_count(self):
        """Количество ожидающих выводов"""
        result = await db.fetchone("SELECT COUNT(*) as count FROM withdrawals WHERE status = 'pending'")
        return result['count'] if result else 0
    
    # Обработчики платежей
    async def handle_pre_checkout(self, pre_checkout_query: PreCheckoutQuery):
        """Обработка предварительной проверки платежа"""
        try:
            await self.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
            logger.info(f"Pre-checkout approved: {pre_checkout_query.id}")
        except Exception as e:
            logger.error(f"Ошибка pre-checkout: {e}")
            await self.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Payment processing failed"
            )
    
    async def handle_successful_payment(self, message: Message):
        """Обработка успешного платежа"""
        try:
            payment = message.successful_payment
            payload = payment.invoice_payload
            
            logger.info(f"Успешный платеж: {payload}")
            
            # Разбираем payload
            if payload.startswith("deposit_"):
                # Обработка депозита
                parts = payload.split("_")
                if len(parts) >= 4:
                    user_id = int(parts[1])
                    amount_xtr = int(parts[2])
                    
                    success = await self.payment_system.process_deposit(
                        user_id,
                        amount_xtr,
                        payment.provider_payment_charge_id,
                        payment.telegram_payment_charge_id
                    )
                    
                    if success:
                        # Уведомляем пользователя
                        exchange = await db.fetchone("SELECT stars_per_xtr FROM exchange_rates WHERE id = 1")
                        stars_per_xtr = exchange['stars_per_xtr'] if exchange else 1000
                        
                        await self.bot.send_message(
                            user_id,
                            f"✅ **Депозит успешен!**\n\n"
                            f"💎 Получено: {amount_xtr} XTR\n"
                            f"⭐ Начислено: {amount_xtr * stars_per_xtr} звезд\n"
                            f"💰 Новый баланс XTR: {await self.get_user_xtr_balance(user_id)}\n\n"
                            f"*Спасибо за пополнение!* 🖤"
                        )
                    else:
                        await self.bot.send_message(
                            user_id,
                            "❌ Ошибка обработки депозита. Обратитесь к администратору."
                        )
            
            elif payload.startswith("buy_stars_"):
                # Обработка покупки звезд
                parts = payload.split("_")
                if len(parts) >= 5:
                    user_id = int(parts[2])
                    amount_stars = int(parts[3])
                    amount_xtr = int(parts[4])
                    
                    success = await self.payment_system.process_deposit(
                        user_id,
                        amount_xtr,
                        payment.provider_payment_charge_id,
                        payment.telegram_payment_charge_id
                    )
                    
                    if success:
                        await self.bot.send_message(
                            user_id,
                            f"✅ **Звезды куплены!**\n\n"
                            f"⭐ Получено: {amount_stars} звезд\n"
                            f"💎 Потрачено: {amount_xtr} XTR\n"
                            f"💰 Новый баланс звезд: {await self.get_user_stars_balance(user_id)}\n\n"
                            f"*Спасибо за покупку!* ✨"
                        )
            
            # Подтверждаем получение платежа
            await message.answer("✅ Платеж успешно обработан!")
            
        except Exception as e:
            logger.error(f"Ошибка обработки платежа: {e}")
            await message.answer("❌ Ошибка обработки платежа")
    
    async def get_user_xtr_balance(self, user_id: int) -> int:
        """Получить баланс XTR пользователя"""
        user = await db.fetchone(
            "SELECT balance_xtr FROM users WHERE user_id = ?",
            (user_id,)
        )
        return user['balance_xtr'] if user else 0
    
    async def get_user_stars_balance(self, user_id: int) -> int:
        """Получить баланс звезд пользователя"""
        user = await db.fetchone(
            "SELECT balance_stars FROM users WHERE user_id = ?",
            (user_id,)
        )
        return user['balance_stars'] if user else 0
    
    # Callback обработчики
    async def handle_deposit_callback(self, callback: CallbackQuery):
        """Обработка callback для депозитов"""
        try:
            data = callback.data
            
            if data == "deposit_menu":
                await self.handle_deposit(callback.message, None)
            
            elif data.startswith("deposit_"):
                amount = data.replace("deposit_", "")
                if amount == "custom":
                    await callback.message.answer("💎 Введите сумму для пополнения (в XTR):")
                    # Здесь можно установить состояние FSM
                else:
                    try:
                        amount_int = int(amount)
                        await self.handle_deposit(callback.message, CommandObject(args=str(amount_int)))
                    except ValueError:
                        await callback.answer("❌ Неверная сумма")
            
            elif data.startswith("check_deposit_"):
                await callback.answer("✅ Проверка платежа...")
                # Здесь можно реализовать проверку статуса платежа
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка в handle_deposit_callback: {e}")
            await callback.answer("❌ Ошибка обработки")
    
    async def handle_nft_callback(self, callback: CallbackQuery):
        """Обработка callback для NFT"""
        try:
            data = callback.data
            
            if data == "nft_shop_menu":
                await self.handle_nft_shop(callback.message)
            
            elif data.startswith("nft_buy_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    payment_type = parts[2]  # xtr или stars
                    nft_id = int(parts[3])
                    
                    user_id = callback.from_user.id
                    
                    # Получаем информацию о NFT
                    nft = await db.fetchone(
                        "SELECT * FROM nft_items WHERE id = ?",
                        (nft_id,)
                    )
                    
                    if not nft:
                        await callback.answer("❌ NFT не найден")
                        return
                    
                    if payment_type == "xtr":
                        price = nft['price_xtr']
                        
                        # Проверяем баланс
                        user = await db.fetchone(
                            "SELECT balance_xtr FROM users WHERE user_id = ?",
                            (user_id,)
                        )
                        
                        if not user or user['balance_xtr'] < price:
                            await callback.answer("❌ Недостаточно XTR")
                            return
                        
                        # Покупаем NFT
                        success, message, _ = await self.payment_system.process_nft_purchase(
                            user_id, nft_id, 'xtr', price
                        )
                        
                        if success:
                            await callback.message.answer(f"✅ {message}")
                        else:
                            await callback.message.answer(f"❌ {message}")
                    
                    elif payment_type == "stars":
                        price = nft['price_stars']
                        
                        # Проверяем баланс
                        user = await db.fetchone(
                            "SELECT balance_stars FROM users WHERE user_id = ?",
                            (user_id,)
                        )
                        
                        if not user or user['balance_stars'] < price:
                            await callback.answer("❌ Недостаточно звезд")
                            return
                        
                        # Покупаем NFT
                        success, message, _ = await self.payment_system.process_nft_purchase(
                            user_id, nft_id, 'stars', price
                        )
                        
                        if success:
                            await callback.message.answer(f"✅ {message}")
                        else:
                            await callback.message.answer(f"❌ {message}")
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка в handle_nft_callback: {e}")
            await callback.answer("❌ Ошибка обработки")
    
    async def handle_withdraw_callback(self, callback: CallbackQuery):
        """Обработка callback для выводов"""
        try:
            data = callback.data
            
            if data == "withdraw_menu":
                await self.handle_withdraw(callback.message, None)
            
            elif data == "withdraw_requests":
                user_id = callback.from_user.id
                
                withdrawals = await db.fetchall('''
                    SELECT * FROM withdrawals 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''', (user_id,))
                
                if not withdrawals:
                    await callback.message.answer("📭 У вас нет заявок на вывод")
                    return
                
                text = "📋 **ВАШИ ЗАЯВКИ НА ВЫВОД**\n\n"
                
                for w in withdrawals:
                    status_emoji = {
                        'pending': '🔄',
                        'processing': '⏳',
                        'completed': '✅',
                        'rejected': '❌',
                        'cancelled': '🚫'
                    }.get(w['status'], '❓')
                    
                    text += f"{status_emoji} Заявка #{w['id']}\n"
                    text += f"💰 Сумма: {w['amount']} XTR\n"
                    text += f"💸 Комиссия: {w['fee']} XTR\n"
                    text += f"🎯 К получению: {w['net_amount']} XTR\n"
                    text += f"📅 Дата: {w['created_at'][:10]}\n"
                    text += f"📝 Статус: {w['status']}\n\n"
                
                await callback.message.answer(text)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка в handle_withdraw_callback: {e}")
            await callback.answer("❌ Ошибка обработки")
    
    async def start(self):
        """Запуск бота"""
        logger.info("Starting XTR Bot...")
        
        # Устанавливаем команды бота
        commands = [
            BotCommand(command="start", description="🚀 Начать работу"),
            BotCommand(command="deposit", description="💎 Пополнить XTR"),
            BotCommand(command="withdraw", description="💸 Вывести XTR"),
            BotCommand(command="balance", description="💰 Мой баланс"),
            BotCommand(command="nft_shop", description="🛒 Магазин NFT"),
            BotCommand(command="my_nfts", description="🎒 Мои NFT"),
            BotCommand(command="exchange", description="💱 Курс обмена"),
            BotCommand(command="help", description="❓ Помощь"),
        ]
        
        if XTRConfig.ADMIN_IDS:
            commands.append(BotCommand(command="admin", description="🛡️ Админ панель"))
        
        await self.bot.set_my_commands(commands)
        
        # Запускаем бота
        await self.dp.start_polling(self.bot)

# ============================================================================
# ВЕБ-ИНТЕРФЕЙС XTR
# ============================================================================

class XTRWebApp:
    """Веб-интерфейс для XTR системы"""
    
    def __init__(self, bot_instance: XTRBot):
        self.app = FastAPI(
            title="Golden Cobra XTR",
            description="Telegram Stars Payment System",
            version="5.0.0"
        )
        
        self.bot = bot_instance
        self.setup_middleware()
        self.setup_routes()
        
        logger.info("XTR Web App initialized")
    
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
            return await self.get_homepage()
        
        @self.app.get("/api/user/{user_id}")
        async def get_user(user_id: int):
            return await self.api_get_user(user_id)
        
        @self.app.get("/api/balance/{user_id}")
        async def get_balance(user_id: int):
            return await self.api_get_balance(user_id)
        
        @self.app.get("/api/nfts")
        async def get_nfts():
            return await self.api_get_nfts()
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "version": "5.0.0", "currency": "XTR"}
    
    async def get_homepage(self) -> str:
        """Главная страница"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Golden Cobra XTR - Telegram Stars</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000;
            color: #ffd700;
            font-family: 'Arial', sans-serif;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 50px 0;
            background: linear-gradient(90deg, #000, #8b0000, #000);
            border-bottom: 3px solid #ffd700;
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 3rem;
            color: #ffd700;
            text-shadow: 0 0 20px #ff0000;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 1.5rem;
            color: #ff6b6b;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin: 50px 0;
        }
        
        .feature {
            background: rgba(139, 0, 0, 0.3);
            border: 2px solid #ffd700;
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s;
        }
        
        .feature:hover {
            transform: translateY(-10px);
            box-shadow: 0 10px 20px rgba(255, 0, 0, 0.3);
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
            border-radius: 15px;
            border: 3px solid #ffd700;
        }
        
        .cta-button {
            display: inline-block;
            background: linear-gradient(45deg, #ffd700, #ff0000);
            color: #000;
            padding: 15px 30px;
            font-size: 1.2rem;
            font-weight: bold;
            text-decoration: none;
            border-radius: 50px;
            margin-top: 20px;
            transition: all 0.3s;
        }
        
        .cta-button:hover {
            transform: scale(1.1);
            box-shadow: 0 0 30px #ff0000;
        }
        
        footer {
            text-align: center;
            padding: 30px;
            margin-top: 50px;
            border-top: 2px solid #8b0000;
            color: #666;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 2rem; }
            .features { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🖤 GOLDEN COBRA XTR 🖤</h1>
            <div class="subtitle">Telegram Stars Payment System</div>
        </header>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">💎</div>
                <div class="feature-title">Real Telegram Stars</div>
                <div class="feature-description">
                    Полноценная интеграция с Telegram Stars (XTR).
                    Принимайте платежи, выводите средства, используйте реальную криптовалюту.
                </div>
            </div>
            
            <div class="feature">
                <div class="feature-icon">🛒</div>
                <div class="feature-title">NFT Marketplace</div>
                <div class="feature-description">
                    Покупайте, продавайте и торгуйте NFT за реальные XTR.
                    Коллекционные предметы с реальной стоимостью.
                </div>
            </div>
            
            <div class="feature">
                <div class="feature-icon">💰</div>
                <div class="feature-title">Instant Withdrawals</div>
                <div class="feature-description">
                    Быстрый вывод заработанных XTR на ваш кошелек.
                    Низкие комиссии, быстрая обработка заявок.
                </div>
            </div>
            
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">High Performance</div>
                <div class="feature-description">
                    Быстрая и надежная система платежей.
                    Поддержка тысяч транзакций в секунду.
                </div>
            </div>
        </div>
        
        <div class="cta">
            <h2>READY TO EARN REAL MONEY?</h2>
            <p>Join our Telegram bot and start earning Telegram Stars today!</p>
            <a href="https://t.me/GoldenCobraXTRBot" class="cta-button" target="_blank">
                🚀 START EARNING XTR
            </a>
        </div>
        
        <footer>
            <p>🖤 Golden Cobra XTR v5.0 | Real Telegram Stars Integration</p>
            <p>© 2024 All rights reserved</p>
        </footer>
    </div>
</body>
</html>
        """
    
    async def api_get_user(self, user_id: int):
        """API: Получить данные пользователя"""
        try:
            user = await db.fetchone('''
                SELECT u.*, 
                       (SELECT COUNT(*) FROM nft_ownership WHERE user_id = u.user_id) as nft_count,
                       (SELECT SUM(amount) FROM xtr_transactions WHERE user_id = u.user_id AND type = 'deposit') as total_deposited
                FROM users u 
                WHERE user_id = ?
            ''', (user_id,))
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "user_id": user['user_id'],
                "username": user['username'],
                "balance_xtr": user['balance_xtr'],
                "balance_stars": user['balance_stars'],
                "total_deposited_xtr": user['total_deposited_xtr'],
                "total_withdrawn_xtr": user['total_withdrawn_xtr'],
                "nft_count": user['nft_count'],
                "is_verified": bool(user['is_verified']),
                "created_at": user['created_at']
            }
        except Exception as e:
            logger.error(f"API error in get_user: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def api_get_balance(self, user_id: int):
        """API: Получить баланс"""
        try:
            user = await db.fetchone(
                "SELECT balance_xtr, balance_stars FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "xtr_balance": user['balance_xtr'],
                "stars_balance": user['balance_stars'],
                "estimated_usd": user['balance_xtr'] * 0.01  # 1 XTR = $0.01
            }
        except Exception as e:
            logger.error(f"API error in get_balance: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def api_get_nfts(self):
        """API: Получить список NFT"""
        try:
            nfts = await db.fetchall('''
                SELECT * FROM nft_items 
                WHERE available = 1 
                ORDER BY price_xtr ASC
            ''')
            
            return {
                "nfts": [
                    {
                        "id": nft['id'],
                        "name": nft['name'],
                        "description": nft['description'],
                        "price_xtr": nft['price_xtr'],
                        "price_stars": nft['price_stars'],
                        "rarity": nft['rarity'],
                        "emoji": nft['emoji'],
                        "stock": nft['stock']
                    }
                    for nft in nfts
                ]
            }
        except Exception as e:
            logger.error(f"API error in get_nfts: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def start(self):
        """Запуск веб-сервера"""
        config = uvicorn.Config(
            self.app,
            host=XTRConfig.WEB_HOST,
            port=XTRConfig.WEB_PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

# ============================================================================
# ОСНОВНОЙ ЗАПУСК
# ============================================================================

async def main():
    """Главная функция запуска"""
    try:
        logger.info("=" * 60)
        logger.info("🖤 STARTING GOLDEN COBRA XTR v5.0 🖤")
        logger.info("=" * 60)
        
        # Создаем экземпляры
        bot = XTRBot()
        web_app = XTRWebApp(bot)
        
        # Запускаем параллельно
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
        logger.info("Golden Cobra XTR shutdown complete")

if __name__ == "__main__":
    # Настройка обработки исключений
    import sys
    sys.excepthook = lambda exc_type, exc_value, exc_traceback: logger.critical(
        f"Uncaught exception: {exc_type.__name__}: {exc_value}"
    )
    
    # Запуск
    asyncio.run(main())
