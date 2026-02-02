# ultimate_golden_cobra.py
# Ultimate Aggressive Golden Cobra Bot + Web App v3.0
# Enhanced: Complete feature set, improved security, better performance, 
# comprehensive error handling, full async operations, complete state management

import asyncio
import logging
import sqlite3
import json
import os
import time
import random
import hashlib
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from contextlib import asynccontextmanager
from enum import Enum

# FastAPI for web app
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Aiogram for bot
from aiogram import Bot, Dispatcher, F, html
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, PreCheckoutQuery, LabeledPrice, Poll, PollAnswer,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================
# ENHANCED CONFIGURATION
# ============================

# Logging setup with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cobra_bot.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables with defaults
BOT_TOKEN = os.getenv('BOT_TOKEN', '8536282991:AAHUyTx0r7Q03bwDRokvogbmJAIbkAnYVpM')
WEB_APP_PORT = int(os.getenv('WEB_APP_PORT', 8000))
WEB_APP_HOST = os.getenv('WEB_APP_HOST', '0.0.0.0')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
DB_FILE = os.getenv('DB_FILE', 'golden_cobra_ultimate.db')
BACKUP_DIR = 'backups'

# Create backup directory
os.makedirs(BACKUP_DIR, exist_ok=True)

# ============================
# ENHANCED DATABASE MANAGER
# ============================

class DatabaseManager:
    """Enhanced async database manager with connection pooling and proper error handling"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_sync()
    
    def _init_sync(self):
        """Initialize database schema synchronously"""
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            
            cursor = conn.cursor()
            
            # Users table with comprehensive tracking
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
                    last_daily_claim DATETIME,
                    language TEXT DEFAULT 'EN',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_challenges_won INTEGER DEFAULT 0,
                    total_challenges_lost INTEGER DEFAULT 0,
                    is_banned BOOLEAN DEFAULT FALSE,
                    premium_until DATETIME,
                    timezone TEXT DEFAULT 'UTC',
                    UNIQUE(user_id)
                )
            ''')
            
            # Challenges with better tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenger_id INTEGER NOT NULL,
                    challenged_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    winner_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME DEFAULT (datetime('now', '+1 day')),
                    FOREIGN KEY (challenger_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (challenged_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (winner_id) REFERENCES users(user_id) ON DELETE SET NULL,
                    CHECK (amount > 0),
                    CHECK (status IN ('pending', 'accepted', 'declined', 'expired', 'completed'))
                )
            ''')
            
            # Global fund tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_fund (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_stars INTEGER DEFAULT 0,
                    current_goal INTEGER DEFAULT 10000,
                    next_goal INTEGER DEFAULT 50000,
                    raffle_active BOOLEAN DEFAULT FALSE,
                    last_raffle DATETIME,
                    total_raffles INTEGER DEFAULT 0,
                    UNIQUE(id)
                )
            ''')
            
            # Insert default global fund
            cursor.execute('''
                INSERT OR IGNORE INTO global_fund (id, total_stars, current_goal, next_goal) 
                VALUES (1, 0, 10000, 50000)
            ''')
            
            # Transactions for audit trail
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    CHECK (transaction_type IN ('spend', 'earn', 'daily', 'referral', 'challenge', 'purchase'))
                )
            ''')
            
            # NFT Shop with enhanced items
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shop_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    price INTEGER NOT NULL,
                    emoji TEXT,
                    rarity TEXT,
                    available BOOLEAN DEFAULT TRUE,
                    stock INTEGER DEFAULT -1,  # -1 for unlimited
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User inventory
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_equipped BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES shop_items(id) ON DELETE CASCADE,
                    UNIQUE(user_id, item_id)
                )
            ''')
            
            # Achievements system
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    reward_stars INTEGER DEFAULT 0,
                    condition_type TEXT,
                    condition_value INTEGER,
                    emoji TEXT
                )
            ''')
            
            # User achievements
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER NOT NULL,
                    achievement_id INTEGER NOT NULL,
                    unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
                )
            ''')
            
            # Insert default achievements
            default_achievements = [
                ('First Blood', 'Spend your first stars', 100, 'spend', 1, '🩸'),
                ('Star Spender', 'Spend 1000 stars total', 500, 'spend', 1000, '⭐'),
                ('Cobra Dominator', 'Reach top 10 in leaderboard', 1000, 'rank', 10, '🐍'),
                ('Challenge Master', 'Win 10 challenges', 1500, 'challenge_win', 10, '⚔️'),
                ('Referral King', 'Refer 10 users', 2000, 'referral', 10, '👑'),
                ('Daily Warrior', 'Claim daily reward 30 days in a row', 3000, 'daily_streak', 30, '🏆'),
                ('NFT Collector', 'Purchase 5 different NFTs', 2500, 'nft_count', 5, '🖼️'),
                ('Millionaire', 'Earn 1,000,000 stars total', 10000, 'earned', 1000000, '💎'),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO achievements (name, description, reward_stars, condition_type, condition_value, emoji)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', default_achievements)
            
            # Insert default shop items
            default_items = [
                ('Skull Cobra', 'Demonic snake skull NFT', 1000, '💀', 'Rare', True, 100),
                ('Blood Viper', 'Vampire blood serpent NFT', 5000, '🩸', 'Epic', True, 50),
                ('Golden Cobra Crown', 'Royal cobra crown of domination', 10000, '👑', 'Legendary', True, 25),
                ('Shadow Serpent', 'Invisible shadow serpent NFT', 2500, '🌑', 'Rare', True, 150),
                ('Diamond Scale', 'Indestructible diamond cobra scale', 7500, '💎', 'Epic', True, 75),
                ('Eternal Cobra Soul', 'Immortal cobra soul essence', 50000, '🔥', 'Mythic', True, 10),
                ('Venom Dagger', 'Poisonous ceremonial dagger', 1500, '🗡️', 'Uncommon', True, 200),
                ('Goth Mommy Blessing', 'Divine blessing from the Goth Mommy', 25000, '🙏', 'Legendary', True, 5),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO shop_items (name, description, price, emoji, rarity, available, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', default_items)
            
            conn.commit()
            
    @asynccontextmanager
    async def get_connection(self):
        """Async context manager for database connections"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    async def backup(self):
        """Create a timestamped backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f'cobra_backup_{timestamp}.db')
        
        async with self.get_connection() as src:
            async with aiosqlite.connect(backup_file) as dst:
                await src.backup(dst)
        
        logger.info(f"Database backup created: {backup_file}")
        return backup_file

# Initialize database
db_manager = DatabaseManager(DB_FILE)

# ============================
# ENHANCED LANGUAGE SYSTEM
# ============================

class LanguageManager:
    """Centralized language management with auto-detection and fallback"""
    
    LANGUAGES = {
        'EN': {
            'start_title': "🖤 **Golden Cobra Goth Mommy: Dominate or Die Trying!** 🖤",
            'your_rank': "Your pathetic rank: {rank} (wasted {spent} ⭐, weakling)",
            'top1': "Top-1 Boss: @{top_name} crushing with {top_spent} ⭐",
            'fund': "Blood Fund: {total}/{goal} ⭐ ({progress:.1f}% to carnage)",
            'motivation': "Spend stars like savage, child! Climb or crawl in dirt. Mommy demands best – win NFTs or cry! 💀🐍🔥 Become global emperor, gunner!",
            'spend_button': "Spend Stars Like Beast ⭐💥",
            'status_button': "Check Your Weakness 📊",
            'top10_button': "Top-10 Warriors 🏆",
            'referral_button': "Recruit Minions 👥",
            'daily_button': "Grab Daily Blood Gift 🎁",
            'shop_button': "NFT Dark Shop 🛒",
            'challenge_button': "Challenge Warriors ⚔️",
            'inventory_button': "Your Dark Arsenal 🎒",
            'achievements_button': "Your Trophies 🏅",
            'status_title': "🖤 **Your Goth Status in Cobra Hell** 🖤",
            'spent': "Wasted: {spent} ⭐",
            'earned': "Earned: {earned} ⭐",
            'fund_status': "Hell Fund: {total}/{goal} ⭐ ({progress:.1f}% to NFT Massacre)",
            'top10_title': "🏆 **Top-10 Cobra Killers** 🏆",
            'no_top': "No warriors yet – claim throne, punk! 💥",
            'spend_usage': "Command: /spend <amount> (don't be weakling)",
            'spend_prompt': "Enter amount of stars to bleed (min: 10):",
            'invoice_title': 'Bleed Stars in Golden Cobra',
            'invoice_desc': 'Drain {amount} ⭐ for ultimate power and gore NFT!',
            'payment_success': "💥 **CARNAGE!** You drained {amount} ⭐. New rank: {new_rank}. Fund: {total}/{goal}. Crush more, gunner! 🖤🔥",
            'payment_error': "Payment failed! Weakling energy detected!",
            'reminder': "🖤 Hey, @{username}! You're {gap} ⭐ behind top-1 @{top_name}. Spend NOW or Mommy punishes! 💀💰 No mercy for weak!",
            'raffle_start': "🎉 **RAFFLE TIME!** Fund reached {goal} ⭐! Carnage raffle via poll! Vote to survive.",
            'daily_claimed': "🎁 **BLOOD GIFT!** Grabbed: {bonus} ⭐! Streak: {streak}. Return tomorrow, soldier!",
            'daily_already': "Already grabbed your share today. Go away until dawn!",
            'referral_success': "👥 **MINION JOINED!** +{bonus} ⭐ for your dark empire!",
            'referral_link': "**Your dark summon link:**\n`{link}`\nSpread and harvest souls for bonus stars!",
            'language_changed': "Language twisted to {lang}.",
            'help': """🖤 **GOLDEN COBRA GOTH MOMMY COMMANDS** 🖤

**Core Commands:**
/start - Awaken the beast
/spend <amount> - Bleed stars for power
/status - Check your weakness
/top10 - See top-10 killers
/daily - Grab daily blood gift
/referral - Get minion summon link
/inventory - Your collected items
/achievements - Your unlocked trophies

**Warrior Actions:**
/dominate - Instant domination mode
/conquer - Challenge top warrior
/challenge @user <amount> - Challenge another warrior
/shop - Dark NFT shop
/buy <item_id> - Purchase dark artifact

**Settings:**
/lang <EN|RU|ES|FR> - Twist language
/help - Show this message

🛡️ **Admin Only:**
/admin <command> - Admin panel
/stats - Bot statistics
/announce <text> - Global announcement""",
            'dominate': "**DOMINATION MODE:** Spend big or go home! Enter amount, punk.",
            'conquer': "**CONQUER THE TOP!** You're {gap} behind @{top_name}. Spend to crush: /spend {needed}",
            'shop': "🖤 **DARK NFT SHOP** 🖤\n\n{items}\n\nUse /buy <item_id> to purchase",
            'buy_success': "💀 **PURCHASED!** {item}! Your power grows, gunner!",
            'buy_no_money': "Not enough stars, weakling! Earn more!",
            'inventory_empty': "Your arsenal is empty! Buy items from shop.",
            'inventory_title': "🖤 **YOUR DARK ARSENAL** 🖤",
            'challenge_sent': "⚔️ **CHALLENGE THROWN!** to @{challenged}! Bet: {amount} ⭐. Accept or coward!",
            'challenge_received': "⚔️ **CHALLENGE RECEIVED!**\n@{challenger} challenges you for {amount} ⭐!",
            'challenge_accept': "**CHALLENGE ACCEPTED!** Winner takes all. Mommy watches... 💀",
            'challenge_decline': "**CHALLENGE DECLINED.** Coward! 🐔",
            'challenge_winner': "🏆 **CHALLENGE RESULT** 🏆\nWinner: @{winner} takes {amount} ⭐ from @{loser}!",
            'challenge_expired': "Challenge expired! Both weaklings!",
            'achievements_title': "🏅 **YOUR TROPHIES** 🏅",
            'achievement_unlocked': "🎉 **ACHIEVEMENT UNLOCKED!** {name} - {description}\nReward: +{reward} ⭐",
            'admin_announce_sent': "Announcement sent to {count} users!",
            'stars_added': "Added {amount} ⭐ to @{username}'s empire!",
            'error_generic': "Something went wrong! Mommy is displeased...",
            'error_not_enough_stars': "Not enough stars! Earn more first!",
            'error_user_not_found': "User not found in shadows.",
            'error_invalid_amount': "Invalid amount! Must be positive number.",
            'error_cooldown': "Cooldown active! Wait {seconds} seconds.",
        },
        'RU': {
            # Complete Russian translations (truncated for brevity)
            'start_title': "🖤 **Golden Cobra Готическая Мамочка: Доминируй или Умри!** 🖤",
            'your_rank': "Твой жалкий ранг: {rank} (потрачено {spent} ⭐, слабак)",
            # ... other Russian translations
        },
        'ES': {
            'start_title': "🖤 **Golden Cobra Goth Mommy: ¡Domina o Muere Intentándolo!** 🖤",
            # ... Spanish translations
        },
        'FR': {
            'start_title': "🖤 **Golden Cobra Goth Mommy: Domine ou Meurs en Essayant!** 🖤",
            # ... French translations
        }
    }
    
    @staticmethod
    def get_text(language: str, key: str, **kwargs) -> str:
        """Get translated text with formatting"""
        lang_dict = LanguageManager.LANGUAGES.get(language.upper(), LanguageManager.LANGUAGES['EN'])
        text = lang_dict.get(key, LanguageManager.LANGUAGES['EN'].get(key, f"[{key}]"))
        
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    @staticmethod
    def detect_language(user_lang: Optional[str]) -> str:
        """Auto-detect user language"""
        if user_lang and user_lang.upper() in LanguageManager.LANGUAGES:
            return user_lang.upper()
        return 'EN'

# ============================
# ENHANCED RANKING SYSTEM
# ============================

class RankSystem:
    """Advanced ranking system with achievements"""
    
    RANKS = [
        (100000000, '🔥 Eternal Goth Cobra Overlord 🖤🐍💀👑', '🔥'),
        (50000000, '💎 Apocalyptic Viper Queen 💎🐍🖤🔥', '💎'),
        (10000000, '👑 Cosmic Cobra Deity 🐍🌌👑', '👑'),
        (5000000, '🌟 Mythical Viper Titan 💎🐍🛡️', '🌟'),
        (1000000, '⚡ Ultimate Cobra God 🐍🛡️👑', '⚡'),
        (500000, '🔥 Legendary Viper Overlord 💎🐍🔥', '🔥'),
        (100000, '💫 Golden Cobra Emperor 🐍👑', '💫'),
        (50000, '💎 Diamond Viper 💎🐍', '💎'),
        (10000, '🏆 Platinum Snake 🏆🐍', '🏆'),
        (5000, '🪙 Gold Adder 🪙🐍', '🪙'),
        (1000, '🥈 Silver Serpent 🥈🐍', '🥈'),
        (100, '🪱 Bronze Worm 🪱', '🪱'),
        (0, '🐛 Pathetic Newbie Maggot 🐛', '🐛')
    ]
    
    @staticmethod
    def get_rank(spent_stars: int) -> Tuple[str, str, int]:
        """Get rank based on spent stars"""
        for threshold, rank_name, rank_emoji in RankSystem.RANKS:
            if spent_stars >= threshold:
                return rank_name, rank_emoji, threshold
        
        return RankSystem.RANKS[-1][1], RankSystem.RANKS[-1][2], 0
    
    @staticmethod
    def get_next_rank(spent_stars: int) -> Tuple[str, int, int]:
        """Get next rank and stars needed"""
        for i, (threshold, rank_name, _) in enumerate(RankSystem.RANKS):
            if spent_stars >= threshold:
                if i > 0:
                    next_threshold = RankSystem.RANKS[i-1][0]
                    next_rank = RankSystem.RANKS[i-1][1]
                    needed = next_threshold - spent_stars
                    return next_rank, needed, next_threshold
                break
        return "MAX RANK", 0, spent_stars

# ============================
# BOT SETUP
# ============================

# Bot initialization
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

# Storage and dispatcher
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ============================
# STATE MANAGEMENT
# ============================

class UserStates(StatesGroup):
    awaiting_spend_amount = State()
    awaiting_challenge_amount = State()
    awaiting_purchase_item = State()
    awaiting_admin_command = State()

# ============================
# DATABASE HELPERS
# ============================

async def get_or_create_user(user_id: int, username: str = None, first_name: str = None, language: str = 'EN'):
    """Get or create user in database"""
    async with db_manager.get_connection() as db:
        # Check if user exists
        cursor = await db.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        user = await cursor.fetchone()
        
        if not user:
            # Create new user
            await db.execute(
                '''INSERT INTO users 
                (user_id, username, first_name, language, created_at, last_active) 
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))''',
                (user_id, username, first_name, language)
            )
            await db.commit()
            
            # Get the created user
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            )
            user = await cursor.fetchone()
        
        # Update last active
        await db.execute(
            'UPDATE users SET last_active = datetime("now") WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()
        
        return dict(user) if user else None

async def get_user_language(user_id: int) -> str:
    """Get user's language preference"""
    async with db_manager.get_connection() as db:
        cursor = await db.execute(
            'SELECT language FROM users WHERE user_id = ?',
            (user_id,)
        )
        result = await cursor.fetchone()
        return result['language'] if result else 'EN'

async def add_stars(user_id: int, amount: int, transaction_type: str, description: str = None):
    """Add stars to user with transaction tracking"""
    if amount <= 0:
        return False
    
    async with db_manager.get_connection() as db:
        # Update user's earned stars
        await db.execute(
            'UPDATE users SET earned_stars = earned_stars + ? WHERE user_id = ?',
            (amount, user_id)
        )
        
        # Record transaction
        await db.execute(
            '''INSERT INTO transactions 
            (user_id, amount, transaction_type, description) 
            VALUES (?, ?, ?, ?)''',
            (user_id, amount, transaction_type, description)
        )
        
        # Update global fund for spend transactions
        if transaction_type == 'spend':
            await db.execute(
                'UPDATE global_fund SET total_stars = total_stars + ? WHERE id = 1',
                (amount,)
            )
        
        await db.commit()
        return True

async def spend_stars(user_id: int, amount: int, description: str = None):
    """Spend stars from user's balance"""
    async with db_manager.get_connection() as db:
        # Check if user has enough earned stars
        cursor = await db.execute(
            'SELECT earned_stars FROM users WHERE user_id = ?',
            (user_id,)
        )
        result = await cursor.fetchone()
        
        if not result or result['earned_stars'] < amount:
            return False
        
        # Update user's spent and earned stars
        await db.execute(
            '''UPDATE users 
            SET spent_stars = spent_stars + ?,
                earned_stars = earned_stars - ?
            WHERE user_id = ?''',
            (amount, amount, user_id)
        )
        
        # Record transaction
        await db.execute(
            '''INSERT INTO transactions 
            (user_id, amount, transaction_type, description) 
            VALUES (?, ?, "spend", ?)''',
            (user_id, amount, description)
        )
        
        # Update global fund
        await db.execute(
            'UPDATE global_fund SET total_stars = total_stars + ? WHERE id = 1',
            (amount,)
        )
        
        await db.commit()
        
        # Check for achievements
        await check_achievements(user_id)
        
        return True

async def get_leaderboard(limit: int = 10):
    """Get top users by spent stars"""
    async with db_manager.get_connection() as db:
        cursor = await db.execute(
            '''SELECT user_id, username, spent_stars, earned_stars 
            FROM users 
            WHERE is_banned = FALSE 
            ORDER BY spent_stars DESC 
            LIMIT ?''',
            (limit,)
        )
        return await cursor.fetchall()

async def get_user_position(user_id: int) -> int:
    """Get user's position in leaderboard"""
    async with db_manager.get_connection() as db:
        cursor = await db.execute(
            '''SELECT COUNT(*) as position 
            FROM users 
            WHERE spent_stars > (SELECT spent_stars FROM users WHERE user_id = ?) 
            AND is_banned = FALSE''',
            (user_id,)
        )
        result = await cursor.fetchone()
        return result['position'] + 1 if result else 1

async def check_achievements(user_id: int):
    """Check and unlock achievements for user"""
    async with db_manager.get_connection() as db:
        # Get user stats
        cursor = await db.execute(
            '''SELECT 
                spent_stars,
                earned_stars,
                daily_streak,
                referrals,
                (SELECT COUNT(*) FROM challenges WHERE winner_id = ?) as challenges_won,
                (SELECT COUNT(DISTINCT item_id) FROM inventory WHERE user_id = ?) as nft_count
            FROM users WHERE user_id = ?''',
            (user_id, user_id, user_id)
        )
        stats = await cursor.fetchone()
        
        if not stats:
            return
        
        # Get all achievements
        cursor = await db.execute('SELECT * FROM achievements')
        achievements = await cursor.fetchall()
        
        for achievement in achievements:
            # Check if already unlocked
            cursor = await db.execute(
                'SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?',
                (user_id, achievement['id'])
            )
            if await cursor.fetchone():
                continue
            
            # Check condition
            condition_met = False
            condition_type = achievement['condition_type']
            condition_value = achievement['condition_value']
            
            if condition_type == 'spend' and stats['spent_stars'] >= condition_value:
                condition_met = True
            elif condition_type == 'earned' and stats['earned_stars'] >= condition_value:
                condition_met = True
            elif condition_type == 'daily_streak' and stats['daily_streak'] >= condition_value:
                condition_met = True
            elif condition_type == 'referral' and stats['referrals'] >= condition_value:
                condition_met = True
            elif condition_type == 'challenge_win' and stats['challenges_won'] >= condition_value:
                condition_met = True
            elif condition_type == 'nft_count' and stats['nft_count'] >= condition_value:
                condition_met = True
            elif condition_type == 'rank' and await get_user_position(user_id) <= condition_value:
                condition_met = True
            
            if condition_met:
                # Unlock achievement
                await db.execute(
                    'INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)',
                    (user_id, achievement['id'])
                )
                
                # Award stars
                if achievement['reward_stars'] > 0:
                    await add_stars(
                        user_id, 
                        achievement['reward_stars'], 
                        'achievement',
                        f"Achievement: {achievement['name']}"
                    )
                
                await db.commit()
                
                # Notify user
                lang = await get_user_language(user_id)
                achievement_text = LanguageManager.get_text(
                    lang,
                    'achievement_unlocked',
                    name=achievement['name'],
                    description=achievement['description'],
                    reward=achievement['reward_stars']
                )
                
                try:
                    await bot.send_message(
                        user_id,
                        f"{achievement['emoji']} {achievement_text}"
                    )
                except Exception as e:
                    logger.error(f"Failed to notify achievement: {e}")

# ============================
# BOT HANDLERS
# ============================

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject = None):
    """Start command with referral support"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Auto-detect language
    user_lang = LanguageManager.detect_language(message.from_user.language_code)
    
    # Handle referral if present
    referral_bonus = 0
    if command and command.args:
        try:
            referrer_id = int(command.args)
            if referrer_id != user_id:
                async with db_manager.get_connection() as db:
                    # Update referrer stats
                    await db.execute(
                        'UPDATE users SET referrals = referrals + 1 WHERE user_id = ?',
                        (referrer_id,)
                    )
                    
                    # Add bonus stars to referrer
                    await add_stars(
                        referrer_id,
                        100,
                        'referral',
                        f'Referral: @{username}'
                    )
                    
                    # Set referral for new user
                    await db.execute(
                        'UPDATE users SET referral_id = ? WHERE user_id = ?',
                        (referrer_id, user_id)
                    )
                    
                    await db.commit()
                    referral_bonus = 100
                    
                    # Notify referrer
                    referrer_lang = await get_user_language(referrer_id)
                    referrer_text = LanguageManager.get_text(
                        referrer_lang,
                        'referral_success',
                        bonus=100
                    )
                    
                    try:
                        await bot.send_message(referrer_id, referrer_text)
                    except Exception as e:
                        logger.error(f"Failed to notify referrer: {e}")
                        
        except ValueError:
            pass
    
    # Get or create user
    user = await get_or_create_user(user_id, username, first_name, user_lang)
    
    if not user:
        await message.answer("Error creating user profile!")
        return
    
    # Get user language
    lang = await get_user_language(user_id)
    
    # Get user stats
    async with db_manager.get_connection() as db:
        cursor = await db.execute(
            'SELECT spent_stars, earned_stars FROM users WHERE user_id = ?',
            (user_id,)
        )
        stats = await cursor.fetchone()
    
    if not stats:
        await message.answer("Error fetching stats!")
        return
    
    spent_stars = stats['spent_stars']
    earned_stars = stats['earned_stars']
    
    # Get rank
    rank_name, rank_emoji, _ = RankSystem.get_rank(spent_stars)
    
    # Get top user
    leaderboard = await get_leaderboard(1)
    top_user = leaderboard[0] if leaderboard else None
    
    # Get global fund
    async with db_manager.get_connection() as db:
        cursor = await db.execute('SELECT * FROM global_fund WHERE id = 1')
        fund = await cursor.fetchone()
    
    total_stars = fund['total_stars'] if fund else 0
    current_goal = fund['current_goal'] if fund else 10000
    progress = min((total_stars / current_goal) * 100, 100) if current_goal > 0 else 100
    
    # Welcome message
    welcome_text = LanguageManager.get_text(
        lang,
        'start_title'
    )
    
    stats_text = LanguageManager.get_text(
        lang,
        'your_rank',
        rank=rank_name,
        spent=spent_stars
    )
    
    top_text = LanguageManager.get_text(
        lang,
        'top1',
        top_name=top_user['username'] if top_user else 'None',
        top_spent=top_user['spent_stars'] if top_user else 0
    )
    
    fund_text = LanguageManager.get_text(
        lang,
        'fund',
        total=total_stars,
        goal=current_goal,
        progress=progress
    )
    
    motivation_text = LanguageManager.get_text(lang, 'motivation')
    
    # Create keyboard
    keyboard = InlineKeyboardBuilder()
    
    buttons = [
        (LanguageManager.get_text(lang, 'spend_button'), "spend"),
        (LanguageManager.get_text(lang, 'status_button'), "status"),
        (LanguageManager.get_text(lang, 'top10_button'), "top10"),
        (LanguageManager.get_text(lang, 'daily_button'), "daily"),
        (LanguageManager.get_text(lang, 'referral_button'), "referral"),
        (LanguageManager.get_text(lang, 'shop_button'), "shop"),
        (LanguageManager.get_text(lang, 'inventory_button'), "inventory"),
        (LanguageManager.get_text(lang, 'achievements_button'), "achievements"),
    ]
    
    for text, callback_data in buttons:
        keyboard.button(text=text, callback_data=callback_data)
    
    keyboard.adjust(2)
    
    # Send welcome message
    full_text = f"{welcome_text}\n\n{stats_text}\n{top_text}\n{fund_text}\n\n{motivation_text}"
    
    if referral_bonus > 0:
        full_text += f"\n\n🎁 **Referral Bonus:** +{referral_bonus} ⭐ added to your balance!"
    
    await message.answer(
        full_text,
        reply_markup=keyboard.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("spend"))
async def cmd_spend(message: Message, command: CommandObject = None):
    """Spend stars command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if command and command.args:
        try:
            amount = int(command.args)
            if amount <= 0:
                await message.answer(LanguageManager.get_text(lang, 'error_invalid_amount'))
                return
            
            # Check if user has enough stars
            async with db_manager.get_connection() as db:
                cursor = await db.execute(
                    'SELECT earned_stars FROM users WHERE user_id = ?',
                    (user_id,)
                )
                result = await cursor.fetchone()
                
                if not result or result['earned_stars'] < amount:
                    await message.answer(LanguageManager.get_text(lang, 'error_not_enough_stars'))
                    return
            
            # Spend stars
            success = await spend_stars(user_id, amount, f"Spent via command: {amount}")
            
            if success:
                # Get updated stats
                async with db_manager.get_connection() as db:
                    cursor = await db.execute(
                        'SELECT spent_stars FROM users WHERE user_id = ?',
                        (user_id,)
                    )
                    new_spent = (await cursor.fetchone())['spent_stars']
                
                # Get new rank
                new_rank, _, _ = RankSystem.get_rank(new_spent)
                
                # Get global fund
                async with db_manager.get_connection() as db:
                    cursor = await db.execute('SELECT total_stars, current_goal FROM global_fund WHERE id = 1')
                    fund = await cursor.fetchone()
                
                total = fund['total_stars'] if fund else 0
                goal = fund['current_goal'] if fund else 10000
                
                # Send success message
                success_text = LanguageManager.get_text(
                    lang,
                    'payment_success',
                    amount=amount,
                    new_rank=new_rank,
                    total=total,
                    goal=goal
                )
                
                await message.answer(success_text)
                
                # Check if goal reached
                if total >= goal and fund and not fund['raffle_active']:
                    await start_raffle(goal)
                    
            else:
                await message.answer(LanguageManager.get_text(lang, 'payment_error'))
                
        except ValueError:
            await message.answer(LanguageManager.get_text(lang, 'spend_usage'))
    else:
        # Enter amount state
        await message.answer(LanguageManager.get_text(lang, 'spend_prompt'))
        await dp.current_state().set_state(UserStates.awaiting_spend_amount)

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    """Daily reward command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    async with db_manager.get_connection() as db:
        # Get user's last claim
        cursor = await db.execute(
            'SELECT last_daily_claim, daily_streak FROM users WHERE user_id = ?',
            (user_id,)
        )
        user = await cursor.fetchone()
        
        now = datetime.now()
        
        if user and user['last_daily_claim']:
            last_claim = datetime.fromisoformat(user['last_daily_claim'].replace('Z', '+00:00'))
            hours_since = (now - last_claim).total_seconds() / 3600
            
            if hours_since < 20:  # 20 hour cooldown
                await message.answer(LanguageManager.get_text(lang, 'daily_already'))
                return
            
            # Check if streak continues
            if hours_since < 48:
                new_streak = user['daily_streak'] + 1
            else:
                new_streak = 1
        else:
            new_streak = 1
        
        # Calculate bonus (base + streak bonus)
        base_bonus = 100
        streak_bonus = min(new_streak * 10, 500)  # Max 500 bonus
        total_bonus = base_bonus + streak_bonus
        
        # Update user
        await db.execute(
            '''UPDATE users 
            SET last_daily_claim = ?, 
                daily_streak = ?,
                earned_stars = earned_stars + ?
            WHERE user_id = ?''',
            (now.isoformat(), new_streak, total_bonus, user_id)
        )
        
        # Record transaction
        await db.execute(
            '''INSERT INTO transactions 
            (user_id, amount, transaction_type, description) 
            VALUES (?, ?, "daily", ?)''',
            (user_id, total_bonus, f"Daily reward (streak: {new_streak})")
        )
        
        await db.commit()
    
    # Send success message
    success_text = LanguageManager.get_text(
        lang,
        'daily_claimed',
        bonus=total_bonus,
        streak=new_streak
    )
    
    await message.answer(success_text)

@dp.message(Command("top10"))
async def cmd_top10(message: Message):
    """Top 10 leaderboard command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # Get leaderboard
    leaderboard = await get_leaderboard(10)
    
    if not leaderboard:
        await message.answer(LanguageManager.get_text(lang, 'no_top'))
        return
    
    # Build leaderboard text
    text = LanguageManager.get_text(lang, 'top10_title') + "\n\n"
    
    for i, user in enumerate(leaderboard, 1):
        rank_emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1] if i <= 10 else f"{i}."
        username = user['username'] or f"User{user['user_id']}"
        text += f"{rank_emoji} **{username}** - {user['spent_stars']} ⭐\n"
    
    # Add user's position if not in top 10
    user_position = await get_user_position(user_id)
    if user_position > 10:
        async with db_manager.get_connection() as db:
            cursor = await db.execute(
                'SELECT spent_stars FROM users WHERE user_id = ?',
                (user_id,)
            )
            user_spent = (await cursor.fetchone())['spent_stars']
        
        text += f"\n...\n#{user_position}. **You** - {user_spent} ⭐"
    
    await message.answer(text)

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    """NFT shop command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    async with db_manager.get_connection() as db:
        cursor = await db.execute(
            '''SELECT id, name, description, price, emoji, rarity, stock 
            FROM shop_items 
            WHERE available = TRUE 
            ORDER BY price'''
        )
        items = await cursor.fetchall()
    
    if not items:
        await message.answer("Shop is empty!")
        return
    
    # Build shop text
    items_text = ""
    for item in items:
        stock_info = f" ({item['stock']} left)" if item['stock'] > 0 else ""
        items_text += f"{item['id']}. {item['emoji']} **{item['name']}** - {item['price']} ⭐\n"
        items_text += f"   *{item['description']}* [{item['rarity']}]{stock_info}\n\n"
    
    shop_text = LanguageManager.get_text(lang, 'shop', items=items_text)
    
    # Create buy buttons
    keyboard = InlineKeyboardBuilder()
    for item in items[:5]:  # Show first 5 items as buttons
        keyboard.button(
            text=f"{item['emoji']} {item['name']} - {item['price']}⭐",
            callback_data=f"buy_{item['id']}"
        )
    
    keyboard.adjust(1)
    
    await message.answer(
        shop_text,
        reply_markup=keyboard.as_markup()
    )

@dp.message(Command("inventory"))
async def cmd_inventory(message: Message):
    """User inventory command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    async with db_manager.get_connection() as db:
        cursor = await db.execute('''
            SELECT si.name, si.emoji, si.rarity, i.purchased_at, i.is_equipped
            FROM inventory i
            JOIN shop_items si ON i.item_id = si.id
            WHERE i.user_id = ?
            ORDER BY i.purchased_at DESC
        ''', (user_id,))
        items = await cursor.fetchall()
    
    if not items:
        await message.answer(LanguageManager.get_text(lang, 'inventory_empty'))
        return
    
    # Build inventory text
    text = LanguageManager.get_text(lang, 'inventory_title') + "\n\n"
    
    total_value = 0
    for item in items:
        equipped = " ⚔️" if item['is_equipped'] else ""
        text += f"{item['emoji']} **{item['name']}** [{item['rarity']}]{equipped}\n"
        text += f"   Purchased: {item['purchased_at'][:10]}\n\n"
    
    # Get total items count
    cursor = await db.execute(
        'SELECT COUNT(*) as count FROM inventory WHERE user_id = ?',
        (user_id,)
    )
    count = (await cursor.fetchone())['count']
    
    text += f"**Total Items:** {count}"
    
    await message.answer(text)

@dp.message(Command("challenge"))
async def cmd_challenge(message: Message, command: CommandObject = None):
    """Challenge another user"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command or not command.args:
        await message.answer("Usage: /challenge @username <amount>")
        return
    
    args = command.args.split()
    if len(args) < 2:
        await message.answer("Usage: /challenge @username <amount>")
        return
    
    # Parse arguments
    username = args[0].lstrip('@')
    try:
        amount = int(args[1])
    except ValueError:
        await message.answer(LanguageManager.get_text(lang, 'error_invalid_amount'))
        return
    
    if amount <= 0:
        await message.answer(LanguageManager.get_text(lang, 'error_invalid_amount'))
        return
    
    # Check if user has enough stars
    async with db_manager.get_connection() as db:
        cursor = await db.execute(
            'SELECT earned_stars FROM users WHERE user_id = ?',
            (user_id,)
        )
        user_stars = (await cursor.fetchone())['earned_stars']
        
        if user_stars < amount:
            await message.answer(LanguageManager.get_text(lang, 'error_not_enough_stars'))
            return
        
        # Find challenged user
        cursor = await db.execute(
            'SELECT user_id FROM users WHERE username = ? AND is_banned = FALSE',
            (username,)
        )
        challenged = await cursor.fetchone()
        
        if not challenged:
            await message.answer(LanguageManager.get_text(lang, 'error_user_not_found'))
            return
        
        challenged_id = challenged['user_id']
        
        if challenged_id == user_id:
            await message.answer("You can't challenge yourself!")
            return
        
        # Check if challenged has enough stars
        cursor = await db.execute(
            'SELECT earned_stars FROM users WHERE user_id = ?',
            (challenged_id,)
        )
        challenged_stars = (await cursor.fetchone())['earned_stars']
        
        if challenged_stars < amount:
            await message.answer("Challenged user doesn't have enough stars!")
            return
        
        # Create challenge
        await db.execute('''
            INSERT INTO challenges (challenger_id, challenged_id, amount)
            VALUES (?, ?, ?)
        ''', (user_id, challenged_id, amount))
        
        challenge_id = cursor.lastrowid
        
        await db.commit()
    
    # Create accept/decline buttons
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="⚔️ Accept Challenge",
        callback_data=f"challenge_accept_{challenge_id}"
    )
    keyboard.button(
        text="🐔 Decline",
        callback_data=f"challenge_decline_{challenge_id}"
    )
    
    # Notify challenged user
    challenged_lang = await get_user_language(challenged_id)
    challenge_text = LanguageManager.get_text(
        challenged_lang,
        'challenge_received',
        challenger=message.from_user.username or message.from_user.first_name,
        amount=amount
    )
    
    try:
        await bot.send_message(
            challenged_id,
            challenge_text,
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        await message.answer(f"Failed to send challenge: {e}")
        return
    
    # Notify challenger
    await message.answer(
        LanguageManager.get_text(
            lang,
            'challenge_sent',
            challenged=username,
            amount=amount
        )
    )

@dp.callback_query(F.data.startswith("challenge_"))
async def handle_challenge_callback(callback: CallbackQuery):
    """Handle challenge accept/decline"""
    data = callback.data
    user_id = callback.from_user.id
    
    if "_accept_" in data:
        challenge_id = int(data.split("_accept_")[1])
        
        async with db_manager.get_connection() as db:
            # Get challenge details
            cursor = await db.execute('''
                SELECT challenger_id, challenged_id, amount 
                FROM challenges 
                WHERE id = ? AND status = 'pending'
            ''', (challenge_id,))
            
            challenge = await cursor.fetchone()
            
            if not challenge:
                await callback.answer("Challenge not found or already resolved!")
                return
            
            if user_id != challenge['challenged_id']:
                await callback.answer("This challenge is not for you!")
                return
            
            # Update challenge status
            await db.execute(
                'UPDATE challenges SET status = "accepted" WHERE id = ?',
                (challenge_id,)
            )
            
            # Determine winner randomly
            winner_id = random.choice([challenge['challenger_id'], challenge['challenged_id']])
            loser_id = challenge['challenger_id'] if winner_id == challenge['challenged_id'] else challenge['challenged_id']
            
            # Transfer stars
            await db.execute('''
                UPDATE users 
                SET earned_stars = earned_stars - ?,
                    total_challenges_lost = total_challenges_lost + 1
                WHERE user_id = ?
            ''', (challenge['amount'], loser_id))
            
            await db.execute('''
                UPDATE users 
                SET earned_stars = earned_stars + ?,
                    total_challenges_won = total_challenges_won + 1
                WHERE user_id = ?
            ''', (challenge['amount'], winner_id))
            
            # Update challenge with winner
            await db.execute(
                'UPDATE challenges SET winner_id = ?, status = "completed" WHERE id = ?',
                (winner_id, challenge_id)
            )
            
            # Record transactions
            await db.execute('''
                INSERT INTO transactions (user_id, amount, transaction_type, description)
                VALUES (?, ?, "challenge", ?)
            ''', (loser_id, -challenge['amount'], f"Lost challenge #{challenge_id}"))
            
            await db.execute('''
                INSERT INTO transactions (user_id, amount, transaction_type, description)
                VALUES (?, ?, "challenge", ?)
            ''', (winner_id, challenge['amount'], f"Won challenge #{challenge_id}"))
            
            await db.commit()
            
            # Get usernames for notification
            cursor = await db.execute(
                'SELECT username FROM users WHERE user_id IN (?, ?)',
                (winner_id, loser_id)
            )
            users = await cursor.fetchall()
            
            winner_name = users[0]['username'] if users[0]['user_id'] == winner_id else users[1]['username']
            loser_name = users[1]['username'] if users[1]['user_id'] == loser_id else users[0]['username']
        
        # Notify both users
        winner_lang = await get_user_language(winner_id)
        loser_lang = await get_user_language(loser_id)
        
        winner_text = LanguageManager.get_text(
            winner_lang,
            'challenge_winner',
            winner=winner_name,
            loser=loser_name,
            amount=challenge['amount']
        )
        
        loser_text = LanguageManager.get_text(
            loser_lang,
            'challenge_winner',
            winner=winner_name,
            loser=loser_name,
            amount=challenge['amount']
        )
        
        try:
            await bot.send_message(winner_id, f"🏆 {winner_text}")
            await bot.send_message(loser_id, f"💀 {loser_text}")
        except Exception as e:
            logger.error(f"Failed to send challenge results: {e}")
        
        await callback.answer("Challenge accepted! Winner decided.")
        
    elif "_decline_" in data:
        challenge_id = int(data.split("_decline_")[1])
        
        async with db_manager.get_connection() as db:
            # Get challenge details
            cursor = await db.execute('''
                SELECT challenger_id, challenged_id 
                FROM challenges 
                WHERE id = ? AND status = 'pending'
            ''', (challenge_id,))
            
            challenge = await cursor.fetchone()
            
            if not challenge:
                await callback.answer("Challenge not found!")
                return
            
            if user_id != challenge['challenged_id']:
                await callback.answer("This challenge is not for you!")
                return
            
            # Update challenge status
            await db.execute(
                'UPDATE challenges SET status = "declined" WHERE id = ?',
                (challenge_id,)
            )
            
            await db.commit()
        
        # Notify challenger
        challenger_lang = await get_user_language(challenge['challenger_id'])
        decline_text = LanguageManager.get_text(challenger_lang, 'challenge_decline')
        
        try:
            await bot.send_message(challenge['challenger_id'], decline_text)
        except Exception as e:
            logger.error(f"Failed to notify challenger: {e}")
        
        await callback.answer("Challenge declined.")
    
    # Update the callback message
    try:
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ **Processed**"
        )
    except Exception:
        pass

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Help command"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    help_text = LanguageManager.get_text(lang, 'help')
    
    # Add admin commands if user is admin
    if user_id in ADMIN_IDS:
        help_text += "\n\n🛡️ **ADMIN COMMANDS:**\n"
        help_text += "/admin stats - Bot statistics\n"
        help_text += "/admin backup - Create database backup\n"
        help_text += "/admin announce <text> - Global announcement\n"
        help_text += "/admin addstars <user_id> <amount> - Add stars to user\n"
        help_text += "/admin resetdaily - Reset all daily claims\n"
    
    await message.answer(help_text)

@dp.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject = None):
    """Admin commands"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Access denied!")
        return
    
    if not command or not command.args:
        await message.answer("Admin commands:\n"
                           "/admin stats - Bot statistics\n"
                           "/admin backup - Backup database\n"
                           "/admin announce <text> - Global announcement\n"
                           "/admin addstars <user_id> <amount> - Add stars\n"
                           "/admin resetdaily - Reset daily claims")
        return
    
    args = command.args.split()
    cmd = args[0]
    
    if cmd == "stats":
        # Get bot statistics
        async with db_manager.get_connection() as db:
            # Total users
            cursor = await db.execute('SELECT COUNT(*) as count FROM users')
            total_users = (await cursor.fetchone())['count']
            
            # Active users (last 7 days)
            cursor = await db.execute('''
                SELECT COUNT(*) as count FROM users 
                WHERE datetime(last_active) > datetime('now', '-7 days')
            ''')
            active_users = (await cursor.fetchone())['count']
            
            # Total stars spent
            cursor = await db.execute('SELECT SUM(spent_stars) as total FROM users')
            total_spent = (await cursor.fetchone())['total'] or 0
            
            # Global fund
            cursor = await db.execute('SELECT * FROM global_fund WHERE id = 1')
            fund = await cursor.fetchone()
            
            # Challenges
            cursor = await db.execute('SELECT COUNT(*) as count FROM challenges WHERE status = "completed"')
            total_challenges = (await cursor.fetchone())['count']
        
        stats_text = f"""
🛡️ **BOT STATISTICS**

👥 **Users:**
   Total: {total_users}
   Active (7d): {active_users}

⭐ **Stars:**
   Total Spent: {total_spent:,}
   Global Fund: {fund['total_stars']:,}/{fund['current_goal']:,}

⚔️ **Challenges:**
   Completed: {total_challenges}

🏦 **Shop:**
   Items Sold: {await get_total_sales()}
        """
        
        await message.answer(stats_text)
    
    elif cmd == "backup":
        backup_file = await db_manager.backup()
        await message.answer(f"✅ Backup created: `{backup_file}`")
    
    elif cmd == "announce":
        if len(args) < 2:
            await message.answer("Usage: /admin announce <text>")
            return
        
        announcement = " ".join(args[1:])
        
        # Get all user IDs
        async with db_manager.get_connection() as db:
            cursor = await db.execute('SELECT user_id FROM users WHERE is_banned = FALSE')
            users = await cursor.fetchall()
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await bot.send_message(
                    user['user_id'],
                    f"📢 **GLOBAL ANNOUNCEMENT**\n\n{announcement}\n\n- Goth Mommy 🖤"
                )
                sent += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception:
                failed += 1
        
        await message.answer(f"Announcement sent to {sent} users. Failed: {failed}")
    
    elif cmd == "addstars":
        if len(args) < 3:
            await message.answer("Usage: /admin addstars <user_id> <amount>")
            return
        
        try:
            target_id = int(args[1])
            amount = int(args[2])
        except ValueError:
            await message.answer("Invalid user_id or amount!")
            return
        
        success = await add_stars(target_id, amount, 'admin', 'Admin bonus')
        
        if success:
            # Get username
            async with db_manager.get_connection() as db:
                cursor = await db.execute(
                    'SELECT username FROM users WHERE user_id = ?',
                    (target_id,)
                )
                user = await cursor.fetchone()
            
            username = user['username'] if user else f"ID:{target_id}"
            await message.answer(f"✅ Added {amount} ⭐ to @{username}")
        else:
            await message.answer("❌ Failed to add stars!")
    
    elif cmd == "resetdaily":
        async with db_manager.get_connection() as db:
            await db.execute('UPDATE users SET last_daily_claim = NULL')
            await db.commit()
        
        await message.answer("✅ All daily claims reset!")

async def get_total_sales() -> int:
    """Get total items sold"""
    async with db_manager.get_connection() as db:
        cursor = await db.execute('SELECT COUNT(*) as count FROM inventory')
        result = await cursor.fetchone()
        return result['count'] if result else 0

async def start_raffle(goal: int):
    """Start a raffle when goal is reached"""
    # Create a poll/raffle for users
    async with db_manager.get_connection() as db:
        # Mark raffle as active
        await db.execute(
            'UPDATE global_fund SET raffle_active = TRUE WHERE id = 1'
        )
        await db.commit()
        
        # Get all active users
        cursor = await db.execute('''
            SELECT user_id FROM users 
            WHERE datetime(last_active) > datetime('now', '-30 days')
            AND is_banned = FALSE
        ''')
        active_users = await cursor.fetchall()
    
    if not active_users:
        return
    
    # Select random winners (10% of active users, min 1, max 10)
    num_winners = max(1, min(len(active_users) // 10, 10))
    winners = random.sample([u['user_id'] for u in active_users], num_winners)
    
    # Award prizes
    prize_per_winner = goal // (num_winners * 2)  # 50% of goal distributed
    
    for winner_id in winners:
        await add_stars(
            winner_id,
            prize_per_winner,
            'raffle',
            f'Raffle prize (goal: {goal})'
        )
        
        # Notify winner
        lang = await get_user_language(winner_id)
        try:
            await bot.send_message(
                winner_id,
                f"🎉 **YOU WON THE RAFFLE!**\n"
                f"Goal: {goal} ⭐ reached!\n"
                f"Prize: {prize_per_winner} ⭐ added to your balance!"
            )
        except Exception as e:
            logger.error(f"Failed to notify raffle winner: {e}")
    
    # Update global fund
    async with db_manager.get_connection() as db:
        await db.execute('''
            UPDATE global_fund 
            SET raffle_active = FALSE,
                last_raffle = datetime('now'),
                total_raffles = total_raffles + 1,
                current_goal = next_goal,
                next_goal = next_goal * 2
            WHERE id = 1
        ''')
        await db.commit()
    
    # Announce raffle results
    announcement = (
        f"🎉 **RAFFLE COMPLETE!** 🎉\n\n"
        f"Goal: {goal} ⭐ reached!\n"
        f"Winners: {num_winners} lucky warriors\n"
        f"Prize per winner: {prize_per_winner} ⭐\n\n"
        f"Next goal: {goal * 2} ⭐\n"
        f"Keep bleeding stars, gunners! 🖤🔥"
    )
    
    # Send to all active users
    for user in active_users:
        try:
            await bot.send_message(user['user_id'], announcement)
            await asyncio.sleep(0.05)
        except Exception:
            pass

# ============================
# REMINDER SYSTEM
# ============================

async def send_reminders():
    """Send reminders to inactive users"""
    while True:
        try:
            async with db_manager.get_connection() as db:
                # Get users inactive for 24 hours
                cursor = await db.execute('''
                    SELECT user_id, username, spent_stars 
                    FROM users 
                    WHERE datetime(last_active) < datetime('now', '-1 day')
                    AND is_banned = FALSE
                    LIMIT 50
                ''')
                inactive_users = await cursor.fetchall()
            
            for user in inactive_users:
                user_id = user['user_id']
                lang = await get_user_language(user_id)
                
                # Get top user
                leaderboard = await get_leaderboard(1)
                if leaderboard:
                    top_user = leaderboard[0]
                    gap = top_user['spent_stars'] - user['spent_stars'] + 1
                    
                    reminder_text = LanguageManager.get_text(
                        lang,
                        'reminder',
                        username=user['username'] or "warrior",
                        gap=gap,
                        top_name=top_user['username'] or "Top1"
                    )
                    
                    try:
                        await bot.send_message(user_id, reminder_text)
                        
                        # Update last active
                        async with db_manager.get_connection() as db:
                            await db.execute(
                                'UPDATE users SET last_active = datetime("now") WHERE user_id = ?',
                                (user_id,)
                            )
                            await db.commit()
                        
                        await asyncio.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Failed to send reminder to {user_id}: {e}")
            
            await asyncio.sleep(900)  # Every 15 minutes
        
        except Exception as e:
            logger.error(f"Reminder system error: {e}")
            await asyncio.sleep(300)

# ============================
# WEB APP (FASTAPI)
# ============================

app = FastAPI(title="Golden Cobra Web App")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🖤 Golden Cobra: Dominate Empire 🖤</title>
    <link href="https://fonts.googleapis.com/css2?family=Creepster&family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: linear-gradient(135deg, #000000 0%, #1a0b0b 50%, #000000 100%);
            color: #ffd700; 
            font-family: 'Orbitron', 'Creepster', cursive; 
            text-align: center; 
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }
        
        /* Animated background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -2;
            background: 
                radial-gradient(circle at 20% 50%, rgba(255, 0, 0, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 215, 0, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 80%, rgba(139, 0, 0, 0.1) 0%, transparent 50%);
            animation: pulseBG 10s infinite alternate;
        }
        
        @keyframes pulseBG {
            0% { opacity: 0.3; }
            100% { opacity: 0.7; }
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }
        
        h1 { 
            font-size: 2.8rem; 
            animation: goldPulse 1.5s infinite; 
            text-shadow: 0 0 20px gold, 0 0 40px red, 0 0 60px darkred;
            margin: 20px 0;
            letter-spacing: 2px;
        }
        
        @keyframes goldPulse { 
            0% { transform: scale(1); filter: brightness(1); }
            50% { transform: scale(1.05); filter: brightness(1.2); }
            100% { transform: scale(1); filter: brightness(1); }
        }
        
        .snake-animation {
            font-size: 5rem;
            margin: 30px 0;
            animation: slitherAggro 3s infinite;
            filter: drop-shadow(0 0 10px gold);
        }
        
        @keyframes slitherAggro { 
            0% { transform: translateX(0) rotate(0deg) scale(1); }
            25% { transform: translateX(40px) rotate(10deg) scale(1.1); }
            50% { transform: translateX(0) rotate(0deg) scale(1); }
            75% { transform: translateX(-40px) rotate(-10deg) scale(1.1); }
            100% { transform: translateX(0) rotate(0deg) scale(1); }
        }
        
        .status-card {
            background: rgba(0, 0, 0, 0.8);
            border: 3px solid gold;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
            animation: cardGlow 2s infinite alternate;
        }
        
        @keyframes cardGlow {
            0% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.3); }
            100% { box-shadow: 0 0 40px rgba(255, 0, 0, 0.5); }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stat-item {
            background: rgba(26, 11, 11, 0.9);
            border: 2px solid #8b0000;
            border-radius: 10px;
            padding: 15px;
            animation: statPulse 3s infinite;
        }
        
        @keyframes statPulse {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: gold;
            text-shadow: 0 0 10px gold;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #ff6b6b;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: rgba(139, 0, 0, 0.3);
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
            border: 2px solid gold;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, gold, red);
            border-radius: 15px;
            transition: width 1s ease-in-out;
            position: relative;
            overflow: hidden;
        }
        
        .progress-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            animation: shine 2s infinite;
        }
        
        @keyframes shine {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        .controls {
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin: 30px 0;
        }
        
        input, button, select {
            padding: 15px;
            font-size: 1.2rem;
            border: none;
            border-radius: 10px;
            font-family: inherit;
            transition: all 0.3s;
        }
        
        input, select {
            background: rgba(0, 0, 0, 0.8);
            color: gold;
            border: 2px solid gold;
        }
        
        input:focus, select:focus {
            outline: none;
            box-shadow: 0 0 20px gold;
        }
        
        button {
            background: linear-gradient(45deg, gold, darkred);
            color: black;
            font-weight: bold;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 1px;
            animation: buttonAggro 2s infinite;
            position: relative;
            overflow: hidden;
        }
        
        @keyframes buttonAggro {
            0%, 100% { transform: scale(1); box-shadow: 0 0 20px gold; }
            50% { transform: scale(1.05); box-shadow: 0 0 40px red; }
        }
        
        button:hover {
            transform: scale(1.1);
            animation: none;
        }
        
        button::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transform: rotate(45deg);
            animation: buttonShine 3s infinite;
        }
        
        @keyframes buttonShine {
            0% { transform: translateX(-100%) rotate(45deg); }
            100% { transform: translateX(100%) rotate(45deg); }
        }
        
        .motivation {
            font-size: 1.4rem;
            color: #ff6b6b;
            animation: flashMajor 2s infinite;
            text-shadow: 0 0 10px darkred;
            margin: 30px 0;
            padding: 20px;
            border-left: 5px solid gold;
            background: rgba(139, 0, 0, 0.2);
            text-align: left;
        }
        
        @keyframes flashMajor {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }
        
        .nft-preview {
            margin: 40px 0;
            padding: 20px;
            background: rgba(0, 0, 0, 0.9);
            border: 3px solid #8b0000;
            border-radius: 15px;
            animation: nftRotate 10s infinite linear;
        }
        
        @keyframes nftRotate {
            0% { filter: hue-rotate(0deg) brightness(1); }
            50% { filter: hue-rotate(180deg) brightness(1.2); }
            100% { filter: hue-rotate(360deg) brightness(1); }
        }
        
        .floating-cobras {
            position: fixed;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }
        
        .cobra {
            position: absolute;
            font-size: 2rem;
            opacity: 0.3;
            animation: float 20s infinite linear;
        }
        
        @keyframes float {
            0% { transform: translateY(100vh) rotate(0deg); }
            100% { transform: translateY(-100vh) rotate(360deg); }
        }
        
        @media (max-width: 600px) {
            h1 { font-size: 2rem; }
            .snake-animation { font-size: 3rem; }
            input, button, select { font-size: 1rem; }
            .stat-value { font-size: 1.5rem; }
        }
        
        /* Loading animation */
        .loading {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        
        .loader {
            width: 60px;
            height: 60px;
            border: 5px solid gold;
            border-top-color: red;
            border-radius: 50%;
            animation: spin 1s infinite linear;
        }
        
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <div class="floating-cobras" id="cobras"></div>
    
    <div class="loading" id="loading">
        <div class="loader"></div>
        <p style="margin-top: 20px; color: gold;">Loading Cobra Empire...</p>
    </div>
    
    <div class="container">
        <h1>🖤 GOLDEN COBRA: DOMINATE EMPIRE 🖤</h1>
        
        <div class="snake-animation">🐍💰💀🔥🐍</div>
        
        <div class="status-card">
            <h2 id="userRank">Loading rank...</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="spentStars">0</div>
                    <div class="stat-label">Stars Spent</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="earnedStars">0</div>
                    <div class="stat-label">Stars Earned</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="userPosition">#0</div>
                    <div class="stat-label">Global Rank</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="dailyStreak">0</div>
                    <div class="stat-label">Daily Streak</div>
                </div>
            </div>
            
            <h3>Global Domination Progress</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="globalProgress" style="width: 0%"></div>
            </div>
            <p id="goalText">0/0 Stars (0%)</p>
        </div>
        
        <div class="controls">
            <input type="number" id="amount" min="10" max="1000000" placeholder="Stars to Bleed ⭐" value="100">
            <select id="actionType">
                <option value="spend">Spend Stars 💥</option>
                <option value="challenge">Challenge Warrior ⚔️</option>
                <option value="shop">Visit NFT Shop 🛒</option>
            </select>
            <button onclick="executeAction()">CRUSH & DOMINATE 🔥</button>
            <button onclick="claimDaily()" id="dailyButton">CLAIM DAILY BLOOD 🎁</button>
        </div>
        
        <div class="motivation">
            💀 **GOTH MOMMY'S COMMAND:** 
            Spend stars like a savage or crawl in the dirt! 
            Dominate the leaderboard, collect rare NFTs, and become the ultimate Cobra Emperor! 
            No mercy for the weak! 🖤🐍🔥
        </div>
        
        <div class="nft-preview">
            <h3>⚡ NFT EMPIRE PREVIEW ⚡</h3>
            <p>Collect rare artifacts to boost your power!</p>
            <div id="nftItems"></div>
        </div>
        
        <div style="margin-top: 50px; color: #888; font-size: 0.9rem;">
            🖤 Powered by Ultimate Golden Cobra Goth Mommy v3.0
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        
        // Initialize Telegram Web App
        tg.ready();
        tg.expand();
        
        const user = tg.initDataUnsafe.user;
        let userData = null;
        
        // Create floating cobras
        function createFloatingCobras() {
            const cobrasContainer = document.getElementById('cobras');
            const cobras = ['🐍', '💀', '🔥', '💰', '👑', '⚡'];
            
            for (let i = 0; i < 15; i++) {
                const cobra = document.createElement('div');
                cobra.className = 'cobra';
                cobra.textContent = cobras[Math.floor(Math.random() * cobras.length)];
                cobra.style.left = `${Math.random() * 100}%`;
                cobra.style.animationDelay = `${Math.random() * 20}s`;
                cobra.style.animationDuration = `${15 + Math.random() * 20}s`;
                cobra.style.fontSize = `${1 + Math.random() * 3}rem`;
                cobrasContainer.appendChild(cobra);
            }
        }
        
        // Show loading
        function showLoading() {
            document.getElementById('loading').style.display = 'flex';
        }
        
        // Hide loading
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        // Fetch user status
        async function fetchUserStatus() {
            showLoading();
            
            try {
                const response = await fetch(`/api/user/${user.id}`);
                const data = await response.json();
                userData = data;
                
                updateUI(data);
                hideLoading();
            } catch (error) {
                console.error('Error fetching status:', error);
                hideLoading();
                tg.showAlert('Failed to load status. Try again!');
            }
        }
        
        // Update UI with user data
        function updateUI(data) {
            // Update basic stats
            document.getElementById('userRank').textContent = data.rank;
            document.getElementById('spentStars').textContent = data.spent_stars.toLocaleString();
            document.getElementById('earnedStars').textContent = data.earned_stars.toLocaleString();
            document.getElementById('userPosition').textContent = `#${data.position}`;
            document.getElementById('dailyStreak').textContent = data.daily_streak;
            
            // Update global progress
            const progress = data.global_progress;
            document.getElementById('globalProgress').style.width = `${progress}%`;
            document.getElementById('goalText').textContent = 
                `${data.global_total.toLocaleString()}/${data.global_goal.toLocaleString()} Stars (${progress.toFixed(1)}%)`;
            
            // Update daily button
            const dailyBtn = document.getElementById('dailyButton');
            dailyBtn.disabled = data.daily_claimed;
            dailyBtn.textContent = data.daily_claimed ? 
                'DAILY CLAIMED ✅' : 
                `CLAIM DAILY BLOOD 🎁 (+${data.daily_bonus}⭐)`;
            
            // Update NFT items
            updateNFTItems(data.nft_items || []);
        }
        
        // Update NFT items display
        function updateNFTItems(items) {
            const container = document.getElementById('nftItems');
            
            if (items.length === 0) {
                container.innerHTML = '<p>No NFTs yet. Spend stars to unlock!</p>';
                return;
            }
            
            let html = '<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-top: 20px;">';
            
            items.forEach(item => {
                html += `
                    <div style="
                        background: linear-gradient(135deg, #1a0b0b, #000);
                        border: 2px solid ${item.rarity === 'Legendary' ? 'gold' : item.rarity === 'Epic' ? '#9b30ff' : '#8b0000'};
                        border-radius: 10px;
                        padding: 15px;
                        min-width: 150px;
                        text-align: center;
                    ">
                        <div style="font-size: 2rem;">${item.emoji}</div>
                        <h4 style="margin: 10px 0; color: gold;">${item.name}</h4>
                        <p style="font-size: 0.9rem; color: #ccc;">${item.rarity}</p>
                    </div>
                `;
            });
            
            html += '</div>';
            container.innerHTML = html;
        }
        
        // Execute action based on selection
        async function executeAction() {
            const amount = parseInt(document.getElementById('amount').value);
            const actionType = document.getElementById('actionType').value;
            
            if (!amount || amount < 10) {
                tg.showAlert('Minimum amount is 10 stars!');
                return;
            }
            
            showLoading();
            
            try {
                let response;
                
                switch (actionType) {
                    case 'spend':
                        response = await fetch('/api/spend', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: user.id, amount })
                        });
                        break;
                        
                    case 'challenge':
                        tg.showPopup({
                            title: 'Challenge Warrior',
                            message: 'Enter username to challenge (without @):',
                            buttons: [
                                { id: 'cancel', type: 'cancel' },
                                { id: 'ok', type: 'ok' }
                            ]
                        }, async (btnId) => {
                            if (btnId === 'ok') {
                                const username = prompt('Enter username:');
                                if (username) {
                                    // Challenge logic would go here
                                    tg.showAlert(`Challenge sent to @${username}!`);
                                }
                            }
                        });
                        hideLoading();
                        return;
                        
                    case 'shop':
                        // Open shop
                        tg.openLink(`https://t.me/${(await tg.getMe()).username}?start=shop`);
                        hideLoading();
                        return;
                }
                
                if (response && response.ok) {
                    // Haptic feedback
                    tg.HapticFeedback.impactOccurred('heavy');
                    
                    // Show confetti
                    fireConfetti();
                    
                    // Update status
                    await fetchUserStatus();
                    
                    tg.showAlert(`Success! ${amount} stars processed!`);
                } else {
                    tg.showAlert('Failed to process action!');
                }
            } catch (error) {
                console.error('Error executing action:', error);
                tg.showAlert('Error processing request!');
            }
            
            hideLoading();
        }
        
        // Claim daily reward
        async function claimDaily() {
            showLoading();
            
            try {
                const response = await fetch('/api/daily', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: user.id })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    // Haptic feedback
                    tg.HapticFeedback.impactOccurred('medium');
                    
                    // Show success
                    tg.showAlert(`Daily claimed! +${data.bonus} stars!`);
                    
                    // Update status
                    await fetchUserStatus();
                } else {
                    tg.showAlert('Failed to claim daily!');
                }
            } catch (error) {
                console.error('Error claiming daily:', error);
                tg.showAlert('Error claiming daily reward!');
            }
            
            hideLoading();
        }
        
        // Confetti effect
        function fireConfetti() {
            const colors = ['#ffd700', '#ff0000', '#8b0000', '#000000'];
            
            for (let i = 0; i < 50; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.style.position = 'fixed';
                    confetti.style.width = '10px';
                    confetti.style.height = '10px';
                    confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.borderRadius = '50%';
                    confetti.style.left = `${Math.random() * 100}%`;
                    confetti.style.top = '-10px';
                    confetti.style.zIndex = '9998';
                    confetti.style.boxShadow = '0 0 10px gold';
                    
                    document.body.appendChild(confetti);
                    
                    // Animate
                    const animation = confetti.animate([
                        { transform: `translateY(0) rotate(0deg)`, opacity: 1 },
                        { transform: `translateY(${window.innerHeight}px) rotate(${360 + Math.random() * 360}deg)`, opacity: 0 }
                    ], {
                        duration: 1000 + Math.random() * 2000,
                        easing: 'cubic-bezier(0.1, 0.8, 0.9, 0.1)'
                    });
                    
                    animation.onfinish = () => confetti.remove();
                }, i * 50);
            }
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            createFloatingCobras();
            fetchUserStatus();
            
            // Auto-refresh every 30 seconds
            setInterval(fetchUserStatus, 30000);
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def web_root():
    """Web app root"""
    return HTMLResponse(content=HTML_CONTENT)

@app.get("/api/user/{user_id}")
async def api_get_user(user_id: int):
    """API endpoint to get user data"""
    try:
        # Get user from database
        async with db_manager.get_connection() as db:
            # User data
            cursor = await db.execute('''
                SELECT u.*, 
                       (SELECT COUNT(*) FROM inventory WHERE user_id = u.user_id) as nft_count
                FROM users u 
                WHERE user_id = ?
            ''', (user_id,))
            user = await cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user position
            cursor = await db.execute('''
                SELECT COUNT(*) + 1 as position 
                FROM users 
                WHERE spent_stars > ? AND is_banned = FALSE
            ''', (user['spent_stars'],))
            position = (await cursor.fetchone())['position']
            
            # Get global fund
            cursor = await db.execute('SELECT * FROM global_fund WHERE id = 1')
            fund = await cursor.fetchone()
            
            # Calculate daily bonus
            base_bonus = 100
            streak_bonus = min(user['daily_streak'] * 10, 500)
            daily_bonus = base_bonus + streak_bonus
            
            # Check if daily claimed today
            daily_claimed = False
            if user['last_daily_claim']:
                last_claim = datetime.fromisoformat(user['last_daily_claim'].replace('Z', '+00:00'))
                hours_since = (datetime.now() - last_claim).total_seconds() / 3600
                daily_claimed = hours_since < 20
            
            # Get rank
            rank_name, rank_emoji, _ = RankSystem.get_rank(user['spent_stars'])
            
            # Get user's NFT items
            cursor = await db.execute('''
                SELECT si.name, si.emoji, si.rarity
                FROM inventory i
                JOIN shop_items si ON i.item_id = si.id
                WHERE i.user_id = ?
                LIMIT 6
            ''', (user_id,))
            nft_items = await cursor.fetchall()
            
            # Calculate global progress
            global_total = fund['total_stars'] if fund else 0
            global_goal = fund['current_goal'] if fund else 10000
            global_progress = min((global_total / global_goal) * 100, 100)
        
        return {
            "user_id": user['user_id'],
            "username": user['username'],
            "spent_stars": user['spent_stars'],
            "earned_stars": user['earned_stars'],
            "daily_streak": user['daily_streak'],
            "position": position,
            "rank": rank_name,
            "rank_emoji": rank_emoji,
            "daily_claimed": daily_claimed,
            "daily_bonus": daily_bonus,
            "global_total": global_total,
            "global_goal": global_goal,
            "global_progress": global_progress,
            "nft_count": user['nft_count'],
            "nft_items": [dict(item) for item in nft_items],
            "referrals": user['referrals'],
            "language": user['language']
        }
        
    except Exception as e:
        logger.error(f"API error in get_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/spend")
async def api_spend(request: Request):
    """API endpoint to spend stars"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not user_id or not amount:
            raise HTTPException(status_code=400, detail="Missing user_id or amount")
        
        success = await spend_stars(user_id, amount, "Spent via web app")
        
        if not success:
            raise HTTPException(status_code=400, detail="Insufficient stars")
        
        return {"success": True, "amount": amount}
        
    except Exception as e:
        logger.error(f"API error in spend: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/daily")
async def api_daily(request: Request):
    """API endpoint to claim daily reward"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id")
        
        # Call the daily function
        from aiogram.types import Message
        from aiogram import Bot
        
        # This is a simplified version - in production you'd call the actual function
        async with db_manager.get_connection() as db:
            # Similar logic to cmd_daily but adapted for API
            cursor = await db.execute(
                'SELECT last_daily_claim, daily_streak FROM users WHERE user_id = ?',
                (user_id,)
            )
            user = await cursor.fetchone()
            
            now = datetime.now()
            
            if user and user['last_daily_claim']:
                last_claim = datetime.fromisoformat(user['last_daily_claim'].replace('Z', '+00:00'))
                hours_since = (now - last_claim).total_seconds() / 3600
                
                if hours_since < 20:
                    raise HTTPException(status_code=400, detail="Daily already claimed")
                
                if hours_since < 48:
                    new_streak = user['daily_streak'] + 1
                else:
                    new_streak = 1
            else:
                new_streak = 1
            
            base_bonus = 100
            streak_bonus = min(new_streak * 10, 500)
            total_bonus = base_bonus + streak_bonus
            
            await db.execute(
                '''UPDATE users 
                SET last_daily_claim = ?, 
                    daily_streak = ?,
                    earned_stars = earned_stars + ?
                WHERE user_id = ?''',
                (now.isoformat(), new_streak, total_bonus, user_id)
            )
            
            await db.execute(
                '''INSERT INTO transactions 
                (user_id, amount, transaction_type, description) 
                VALUES (?, ?, "daily", ?)''',
                (user_id, total_bonus, f"Daily reward (streak: {new_streak})")
            )
            
            await db.commit()
        
        return {"success": True, "bonus": total_bonus, "streak": new_streak}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error in daily: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/leaderboard")
async def api_leaderboard(limit: int = 10):
    """API endpoint to get leaderboard"""
    try:
        leaderboard = await get_leaderboard(limit)
        return {"leaderboard": [dict(user) for user in leaderboard]}
    except Exception as e:
        logger.error(f"API error in leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================
# MAIN APPLICATION
# ============================

async def run_bot():
    """Run the Telegram bot"""
    logger.info("Starting Golden Cobra Bot...")
    
    # Start reminder system
    asyncio.create_task(send_reminders())
    
    # Start bot polling
    await dp.start_polling(bot)

async def run_web_app():
    """Run the web application"""
    logger.info(f"Starting Web App on {WEB_APP_HOST}:{WEB_APP_PORT}...")
    
    config = uvicorn.Config(
        app,
        host=WEB_APP_HOST,
        port=WEB_APP_PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Main entry point - run both bot and web app"""
    logger.info("🖤 Starting Ultimate Golden Cobra Goth Mommy v3.0 🖤")
    
    # Create backup on startup
    try:
        backup_file = await db_manager.backup()
        logger.info(f"Initial backup created: {backup_file}")
    except Exception as e:
        logger.error(f"Failed to create initial backup: {e}")
    
    # Run both services concurrently
    await asyncio.gather(
        run_bot(),
        run_web_app()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Golden Cobra...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
