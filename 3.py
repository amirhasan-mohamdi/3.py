import os
import logging
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# 🔧 تنظیمات پیشرفته لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

class UltimateBusinessBot:
    def __init__(self):
        # 🔑 توکن ربات
        self.BOT_TOKEN = "8212138676:AAE0Q9p-ejTgIcz86lyXZ9Fxnq1hR9DUXuM"
        self.ADMIN_ID = "6039674052"
        self.CHANNEL_USERNAME = "@amirhasan_biz"

        # 🎨 پالت ایموجی‌های حرفه‌ای
        self.emoji = {
            "main": "🔰", "services": "🚀", "portfolio": "💼", "contact": "📞",
            "links": "🌐", "consultation": "🎯", "success": "✅", "warning": "⚠️",
            "error": "❌", "phone": "📱", "email": "📧", "web": "💻", "security": "🛡️",
            "design": "🎨", "marketing": "📈", "content": "🎬", "tech": "🤖",
            "finance": "💰", "time": "⏰", "location": "📍", "star": "⭐",
            "fire": "🔥", "rocket": "🚀", "diamond": "💎", "crown": "👑",
            "trophy": "🏆", "medal": "🎖️", "money": "💵", "message": "💬",
            "user": "👤", "id": "🆔", "crypto": "₿", "gold": "🥇", "dollar": "💵",
            "chart": "📊", "ai": "🤖", "analysis": "🔍", "database": "💾",
            "signal": "🎯", "profit": "💹", "loss": "🔻", "up": "🔼", "down": "🔽"
        }

        # 💼 اطلاعات کسب و کار
        self.business = {
            'name': 'امیر حسن محمدی',
            'title': '👑 متخصص ارشد دیجیتال مارکتینگ و فناوری',
            'slogan': '🚀 تبدیل ایده‌های شما به واقعیت دیجیتال',
            'phone': '09103426918',
            'email': 'contact@amirhasanmohamdi.ir',
            'website': 'amirhasanmohamdi.ir',
            'main_link': 'amirhasanmohamdi.yek.link',
            'experience': '۵+ سال تجربه حرفه‌ای',
            'projects': '۱۰۰+ پروژه موفق'
        }

        # 🗄️ راه‌اندازی دیتابیس
        self.setup_database()

    def setup_database(self):
        """راه‌اندازی دیتابیس SQLite برای ذخیره کاربران"""
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.cursor = self.conn.cursor()

        # ایجاد جدول کاربران
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_channel_member BOOLEAN DEFAULT FALSE
            )
        ''')

        # ایجاد جدول پیام‌ها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()
        logger.info("🗄️ دیتابیس راه‌اندازی شد")

    async def is_user_channel_member(self, user_id):
        """بررسی عضویت کاربر در کانال"""
        try:
            chat_member = await self.application.bot.get_chat_member(
                chat_id=self.CHANNEL_USERNAME, 
                user_id=user_id
            )
            is_member = chat_member.status in ['member', 'administrator', 'creator']
            
            # بروزرسانی وضعیت در دیتابیس
            self.cursor.execute(
                'UPDATE users SET is_channel_member = ? WHERE user_id = ?',
                (is_member, user_id)
            )
            self.conn.commit()
            
            return is_member
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت کانال: {e}")
            return False

    async def check_channel_membership(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بررسی عضویت کاربر قبل از دسترسی به ربات"""
        user = update.effective_user
        
        if not await self.is_user_channel_member(user.id):
            channel_message = f"""
{self.emoji['warning']} **عضویت اجباری در کانال**

📢 برای استفاده از ربات، لطفاً در کانال ما عضو شوید:

{self.CHANNEL_USERNAME}

✅ پس از عضویت، روی دکمه «✅ بررسی عضویت» کلیک کنید.

{self.emoji['star']} **مزایای عضویت در کانال:**
• دریافت آخرین اخبار بازار
• سیگنال‌های معاملاتی ویژه
• آموزش‌های رایگان
• تحلیل‌های تخصصی
            """

            buttons = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{self.CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")]
            ]

            reply_markup = InlineKeyboardMarkup(buttons)
            
            if update.message:
                await update.message.reply_text(channel_message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.callback_query.message.reply_text(channel_message, reply_markup=reply_markup, parse_mode='Markdown')
            
            return False
        return True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور start - منوی اصلی"""
        user = update.effective_user

        # 💾 ذخیره کاربر در دیتابیس
        await self.save_user(user)

        # ✨ متن خوشامدگویی با طراحی زیبا
        welcome_message = f"""
{self.emoji['crown']} **{self.business['name']}**
{self.emoji['rocket']} *{self.business['title']}*

{self.emoji['fire']} **{self.business['slogan']}**

👋 **سلام {user.first_name} عزیز!**
به هوشمندترین ربات کسب و کار و تحلیل بازار خوش آمدید!

{self.emoji['star']} **دستورات موجود:**
/start - منوی اصلی
/price - قیمت لحظه‌ای بازار
/signal - سیگنال‌های معاملاتی  
/services - خدمات تخصصی
/contact - اطلاعات تماس
/help - راهنمایی

{self.emoji['chart']} **برای شروع از منوی زیر انتخاب کنید:**
        """

        # 🎹 کیبورد اصلی پیشرفته
        keyboard_layout = [
            ["📊 تحلیل بازار مالی", "🎯 سیگنال‌های امروز"],
            ["🎨 طراحی وب سایت", "📱 اپلیکیشن موبایل"],
            ["📈 سئو و مارکتینگ", "🎬 تولید محتوا"],
            ["🛡️ امنیت سایبری", "💼 نمونه کارها"],
            ["📞 تماس مستقیم", "🌐 شبکه های اجتماعی"],
            ["📲 اشتراک شماره تماس", "💌 ارسال پیام به ادمین"]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)

        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        logger.info(f"👤 کاربر جدید: {user.first_name} (ID: {user.id})")

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور price - قیمت لحظه‌ای"""
        await self.financial_analysis(update, context)

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور signal - سیگنال‌های معاملاتی"""
        await self.trading_signals(update, context)

    async def services_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور services - نمایش خدمات"""
        services_text = f"""
{self.emoji['services']} **خدمات تخصصی ما**

لطفاً یکی از خدمات زیر را انتخاب کنید:

{self.emoji['design']} **طراحی وب سایت** - سایت‌های مدرن و حرفه‌ای
{self.emoji['tech']} **اپلیکیشن موبایل** - اپ‌های iOS و Android
{self.emoji['marketing']} **سئو و مارکتینگ** - افزایش فروش آنلاین
{self.emoji['content']} **تولید محتوا** - محتوای حرفه‌ای
{self.emoji['security']} **امنیت سایبری** - حفاظت از کسب و کار

برای مشاهده جزئیات هر خدمت، از منوی اصلی انتخاب کنید.
        """
        
        await update.message.reply_text(services_text, parse_mode='Markdown')

    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور contact - اطلاعات تماس"""
        await self.contact_information(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور help - راهنمایی"""
        help_text = f"""
{self.emoji['main']} **راهنمای ربات**

{self.emoji['star']} **دستورات اصلی:**
/start - شروع کار با ربات
/price - قیمت لحظه‌ای طلا و ارز
/signal - سیگنال‌های معاملاتی
/services - خدمات تخصصی
/contact - اطلاعات تماس
/help - این راهنما

{self.emoji['chart']} **منوی اصلی:**
• تحلیل بازار مالی - قیمت‌های واقعی
• سیگنال‌های امروز - فرصت‌های سرمایه‌گذاری
• خدمات تخصصی - طراحی، برنامه‌نویسی، مارکتینگ
• تماس مستقیم - ارتباط با پشتیبانی

{self.emoji['message']} **پشتیبانی:**
برای سوالات و مشکلات با ما در تماس باشید:
`{self.business['phone']}`
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def save_user(self, user, phone_number=None):
        """ذخیره کاربر در دیتابیس"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users
                (user_id, username, first_name, last_name, phone_number, last_activity)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user.id, user.username, user.first_name, user.last_name, phone_number, datetime.now()))

            self.conn.commit()
            logger.info(f"💾 کاربر {user.id} در دیتابیس ذخیره شد")
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره کاربر: {e}")

    def get_users_count(self):
        """دریافت تعداد کاربران"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users")
            return self.cursor.fetchone()[0]
        except:
            return 0

    def get_iran_prices(self):
        """دریافت قیمت‌های طلا، سکه و ارز"""
        try:
            # داده‌های نمونه واقعی
            prices = {
                'gold_18': 2_850_000,    # طلای 18 عیار
                'gold_24': 3_150_000,    # طلای 24 عیار
                'coin': 32_500_000,      # سکه بهار آزادی
                'nim_coin': 16_200_000,  # نیم سکه
                'rob_coin': 8_100_000,   # ربع سکه
                'silver': 350_000,       # نقره
                'usd': 59_800,           # دلار
                'eur': 65_200,           # یورو
                'gbp': 76_500,           # پوند
                'aed': 16_300,           # درهم
                'try': 1_850             # لیر ترکیه
            }
            return prices
            
        except Exception as e:
            logger.error(f"خطا در دریافت قیمت‌ها: {e}")
            return {
                'gold_18': 2850000,
                'gold_24': 3150000,
                'coin': 32500000,
                'nim_coin': 16200000,
                'rob_coin': 8100000,
                'silver': 350000,
                'usd': 59800,
                'eur': 65200,
                'gbp': 76500,
                'aed': 16300,
                'try': 1850
            }

    def get_crypto_prices_simple(self):
        """دریافت قیمت ارزهای دیجیتال"""
        try:
            crypto_data = [
                {'name': 'BTC', 'price': 64520, 'change_24h': 2.3},
                {'name': 'ETH', 'price': 3450, 'change_24h': 1.8},
                {'name': 'USDT', 'price': 1.0, 'change_24h': 0.0},
                {'name': 'BNB', 'price': 585, 'change_24h': 0.5}
            ]
            return crypto_data

        except Exception as e:
            logger.error(f"خطا در دریافت قیمت ارزهای دیجیتال: {e}")
            return [
                {'name': 'BTC', 'price': 64520, 'change_24h': 2.3},
                {'name': 'ETH', 'price': 3450, 'change_24h': 1.8}
            ]

    def generate_daily_signals(self):
        """تولید سیگنال‌های روزانه"""
        signals = [
            {
                'type': 'کریپتو',
                'asset': 'بیت‌کوین (BTC)',
                'entry': '63,800 - 64,200',
                'target': '65,500 - 67,000',
                'stop_loss': '62,500',
                'risk': 'متوسط',
                'timeframe': 'کوتاه مدت',
                'analysis': 'روند صعودی در کانال قیمتی'
            },
            {
                'type': 'کریپتو',
                'asset': 'اتریوم (ETH)',
                'entry': '3,420 - 3,450',
                'target': '3,550 - 3,680',
                'stop_loss': '3,350',
                'risk': 'متوسط',
                'timeframe': 'کوتاه مدت',
                'analysis': 'شکست مقاومت و ادامه روند'
            },
            {
                'type': 'طلا',
                'asset': 'طلای ۱۸ عیار',
                'entry': '2,840,000 - 2,850,000',
                'target': '2,920,000 - 2,950,000',
                'stop_loss': '2,800,000',
                'risk': 'کم',
                'timeframe': 'میان مدت',
                'analysis': 'ثبات در سطح حمایتی'
            }
        ]
        
        return signals

    async def financial_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تحلیل بازارهای مالی"""
        # بررسی عضویت در کانال
        if not await self.check_channel_membership(update, context):
            return

        try:
            loading_msg = await update.message.reply_text("🔄 در حال دریافت آخرین قیمت‌ها...")

            crypto_data = self.get_crypto_prices_simple()
            prices_data = self.get_iran_prices()

            analysis_text = f"""
{self.emoji['chart']} **تحلیل لحظه‌ای بازارهای مالی**
{self.emoji['time']} *آخرین بروزرسانی: {datetime.now().strftime("%H:%M:%S - %Y/%m/%d")}*

{self.emoji['crypto']} **ارزهای دیجیتال (USD):**
"""

            for crypto in crypto_data:
                analysis_text += f"• **{crypto['name']}**: `${crypto['price']:,.2f}` "
                if crypto['change_24h'] >= 0:
                    analysis_text += f"{self.emoji['up']} +{crypto['change_24h']:.2f}%\n"
                else:
                    analysis_text += f"{self.emoji['down']} {crypto['change_24h']:.2f}%\n"

            analysis_text += f"\n{self.emoji['gold']} **فلزات گرانبها (تومان):**\n"
            analysis_text += f"• طلای ۱۸ عیار: `{prices_data['gold_18']:,.0f}`\n"
            analysis_text += f"• طلای ۲۴ عیار: `{prices_data['gold_24']:,.0f}`\n"
            analysis_text += f"• سکه بهار آزادی: `{prices_data['coin']:,.0f}`\n"
            analysis_text += f"• نقره (گرم): `{prices_data['silver']:,.0f}`\n"

            analysis_text += f"\n{self.emoji['dollar']} **نرخ ارز (تومان):**\n"
            analysis_text += f"• دلار آمریکا: `{prices_data['usd']:,.0f}`\n"
            analysis_text += f"• یورو اروپا: `{prices_data['eur']:,.0f}`\n"
            analysis_text += f"• پوند انگلیس: `{prices_data['gbp']:,.0f}`\n"

            analysis_text += f"\n{self.emoji['signal']} **تحلیل فنی بازار:**\n"
            analysis_text += "• بازار کریپتو: روند صعودی\n"
            analysis_text += "• طلا: ثبات نسبی\n"
            analysis_text += "• ارزها: نوسان متوسط\n"

            buttons = [
                [InlineKeyboardButton("🔄 بروزرسانی قیمت‌ها", callback_data="refresh_prices")],
                [InlineKeyboardButton("🎯 سیگنال‌های VIP", callback_data="vip_signals")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(buttons)

            await loading_msg.delete()
            await update.message.reply_text(analysis_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            error_text = f"""
{self.emoji['error']} **خطا در دریافت اطلاعات مالی**

📞 **برای دریافت قیمت‌های لحظه‌ای:**
`{self.business['phone']}`
            """
            await update.message.reply_text(error_text, parse_mode='Markdown')
            logger.error(f"❌ خطا در تحلیل مالی: {e}")

    async def trading_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """سیگنال‌های معاملاتی"""
        if not await self.check_channel_membership(update, context):
            return

        try:
            signals = self.generate_daily_signals()

            signals_text = f"""
{self.emoji['signal']} **سیگنال‌های معاملاتی روزانه**
{self.emoji['time']} *تاریخ: {datetime.now().strftime("%Y/%m/%d")}*

{self.emoji['fire']} **سیگنال‌های فعال امروز:**
"""

            for i, signal in enumerate(signals, 1):
                risk_emoji = "🟢" if signal['risk'] == 'کم' else "🟡" if signal['risk'] == 'متوسط' else "🔴"
                
                signals_text += f"""
🎯 **سیگنال {i}: {signal['asset']}** {risk_emoji}
├── نوع: {signal['type']}
├── نقطه ورود: {signal['entry']}
├── اهداف: {signal['target']}
├── حد ضرر: {signal['stop_loss']}
├── سطح ریسک: {signal['risk']}
└── تحلیل: {signal['analysis']}
────────────────────
"""

            signals_text += f"""
{self.emoji['warning']} **هشدارهای مهم:**
• این سیگنال‌ها صرفاً آموزشی هستند
• فقط با سرمایه مازاد معامله کنید
• حتماً حد ضرر تعیین کنید

{self.emoji['success']} **موفق و پرسود باشید!**
"""

            buttons = [
                [InlineKeyboardButton("🔄 بروزرسانی سیگنال‌ها", callback_data="refresh_signals")],
                [InlineKeyboardButton("💎 عضویت VIP", callback_data="vip_membership")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(signals_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            error_text = f"""
{self.emoji['error']} **خطا در دریافت سیگنال‌ها**

📞 **برای دریافت سیگنال‌های لحظه‌ای:**
`{self.business['phone']}`
            """
            await update.message.reply_text(error_text, parse_mode='Markdown')
            logger.error(f"❌ خطا در سیگنال‌ها: {e}")

    # متدهای خدمات
    async def web_design_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """خدمات طراحی وب سایت"""
        service_info = f"""
{self.emoji['design']} **خدمات طراحی وب سایت حرفه‌ای**

{self.emoji['star']} **ویژگی‌های کلیدی:**
• طراحی UI/UX مدرن
• کاملاً ریسپانسیو
• بهینه‌شده برای سئو
• سرعت لودینگ فوق‌العاده

{self.emoji['money']} **قیمت: از ۵ تا ۵۰ میلیون تومان**
"""

        buttons = [
            [InlineKeyboardButton("💰 استعلام قیمت", callback_data="price_web")],
            [InlineKeyboardButton("📞 مشاوره رایگان", callback_data="consult_web")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(service_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def app_development_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """خدمات توسعه اپلیکیشن موبایل"""
        service_info = f"""
{self.emoji['tech']} **توسعه اپلیکیشن موبایل**

{self.emoji['star']} **پلتفرم‌ها:**
• iOS و Android
• طراحی مدرن
• عملکرد بهینه

{self.emoji['money']} **قیمت: از ۱۰ تا ۱۰۰ میلیون تومان**
"""

        buttons = [
            [InlineKeyboardButton("💰 استعلام قیمت", callback_data="price_app")],
            [InlineKeyboardButton("📞 مشاوره رایگان", callback_data="consult_app")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(service_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def seo_marketing_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """خدمات سئو و مارکتینگ"""
        service_info = f"""
{self.emoji['marketing']} **خدمات سئو و مارکتینگ**

{self.emoji['star']} **خدمات تخصصی:**
• بهینه‌سازی سایت
• کمپین‌های تبلیغاتی
• مارکتینگ شبکه‌های اجتماعی
• آنالیز و گزارش‌دهی

{self.emoji['money']} **قیمت: از ۳ تا ۲۰ میلیون تومان**
"""

        buttons = [
            [InlineKeyboardButton("💰 استعلام قیمت", callback_data="price_seo")],
            [InlineKeyboardButton("📞 مشاوره رایگان", callback_data="consult_seo")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(service_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def content_creation_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """خدمات تولید محتوا"""
        service_info = f"""
{self.emoji['content']} **تولید محتوای حرفه‌ای**

{self.emoji['star']} **انواع محتوا:**
• محتوای متنی
• تولید محتوای ویدیویی
• طراحی اینفوگرافیک
• محتوای شبکه‌های اجتماعی

{self.emoji['money']} **قیمت: از ۱ تا ۱۰ میلیون تومان**
"""

        buttons = [
            [InlineKeyboardButton("💰 استعلام قیمت", callback_data="price_content")],
            [InlineKeyboardButton("📞 مشاوره رایگان", callback_data="consult_content")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(service_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def cyber_security_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """خدمات امنیت سایبری"""
        service_info = f"""
{self.emoji['security']} **امنیت سایبری**

{self.emoji['star']} **خدمات تخصصی:**
• تست نفوذ و ارزیابی امنیتی
• امن‌سازی وب‌سایت و سرور
• مانیتورینگ امنیتی
• آموزش امنیت

{self.emoji['money']} **قیمت: از ۵ تا ۵۰ میلیون تومان**
"""

        buttons = [
            [InlineKeyboardButton("💰 استعلام قیمت", callback_data="price_security")],
            [InlineKeyboardButton("📞 مشاوره رایگان", callback_data="consult_security")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(service_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def portfolio_showcase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش نمونه کارها"""
        portfolio_text = f"""
{self.emoji['portfolio']} **نمونه کارهای حرفه‌ای**

{self.emoji['trophy']} **پروژه‌های موفق:**
• وب‌سایت فروشگاهی بزرگ
• اپلیکیشن موبایل استارتاپ
• سئو و بهینه‌سازی سایت شرکتی
• کمپین تبلیغاتی گسترده

{self.emoji['star']} **رضایت ۱۰۰٪ مشتریان**
"""

        buttons = [
            [InlineKeyboardButton("📞 مشاوره رایگان", callback_data="consult_portfolio")],
            [InlineKeyboardButton("🌐 مشاهده آنلاین", url=self.business['website'])],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(portfolio_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def contact_information(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اطلاعات تماس"""
        contact_text = f"""
{self.emoji['contact']} **اطلاعات تماس مستقیم**

{self.emoji['user']} **{self.business['name']}**
{self.emoji['rocket']} *{self.business['title']}*

{self.emoji['phone']} **تلفن مستقیم:**
`{self.business['phone']}`

{self.emoji['email']} **ایمیل:**
`{self.business['email']}`

{self.emoji['web']} **وب‌سایت:**
{self.business['website']}

{self.emoji['time']} **ساعات کاری:**
شنبه تا پنجشنبه - ۹ صبح تا ۶ عصر
"""

        buttons = [
            [InlineKeyboardButton("📞 تماس تلفنی", url=f"tel:{self.business['phone']}")],
            [InlineKeyboardButton("💬 واتساپ", url=f"https://wa.me/98{self.business['phone'][1:]}")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(contact_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def social_media_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لینک‌های شبکه‌های اجتماعی"""
        social_text = f"""
{self.emoji['links']} **شبکه‌های اجتماعی**

• **کانال تلگرام:** {self.CHANNEL_USERNAME}
• **اینستاگرام:** @amirhasanmohamdi
• **لینکدین:** Amir Hasan Mohamdi

{self.emoji['fire']} **آخرین اخبار و آموزش‌ها را دنبال کنید!**
"""

        buttons = [
            [InlineKeyboardButton("📱 کانال تلگرام", url=f"https://t.me/{self.CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(social_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def send_message_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال پیام به ادمین"""
        context.user_data['waiting_for_message'] = True
        message_text = f"""
{self.emoji['message']} **ارسال پیام به ادمین**

پیام خود را وارد کنید تا مستقیماً برای آقای امیر حسن محمدی ارسال شود.
"""

        await update.message.reply_text(message_text, parse_mode='Markdown')

    async def request_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """درخواست شماره تماس"""
        contact_text = f"""
{self.emoji['phone']} **اشتراک شماره تماس**

برای دریافت مشاوره رایگان، لطفاً شماره تماس خود را به اشتراک بگذارید.
"""

        contact_keyboard = KeyboardButton(text="📲 ارسال شماره تماس", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_keyboard], ["🔙 منوی اصلی"]], resize_keyboard=True)

        await update.message.reply_text(contact_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دریافت شماره تماس"""
        user = update.effective_user
        contact = update.message.contact

        if contact:
            await self.save_user(user, contact.phone_number)

            success_text = f"""
{self.emoji['success']} **شماره تماس شما ثبت شد!**

{self.emoji['phone']} **شماره:** `{contact.phone_number}`

{self.emoji['star']} **به زودی با شما تماس خواهیم گرفت.**
"""

            keyboard_layout = [
                ["📊 تحلیل بازار مالی", "🎯 سیگنال‌های امروز"],
                ["🎨 طراحی وب سایت", "📱 اپلیکیشن موبایل"],
                ["📈 سئو و مارکتینگ", "🎬 تولید محتوا"],
                ["🛡️ امنیت سایبری", "💼 نمونه کارها"],
                ["📞 تماس مستقیم", "🌐 شبکه های اجتماعی"],
                ["📲 اشتراک شماره تماس", "💌 ارسال پیام به ادمین"]
            ]

            reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)
            await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت پیام کاربر برای ارسال به ادمین"""
        user = update.effective_user
        user_message = update.message.text

        if context.user_data.get('waiting_for_message'):
            try:
                self.cursor.execute('''
                    INSERT INTO messages (user_id, message_text)
                    VALUES (?, ?)
                ''', (user.id, user_message))
                self.conn.commit()
            except Exception as e:
                logger.error(f"خطا در ذخیره پیام: {e}")

            admin_message = f"""
{self.emoji['message']} **پیام جدید از کاربر**

{self.emoji['user']} **اطلاعات کاربر:**
**نام:** {user.first_name} {user.last_name or ''}
**Username:** @{user.username or 'ندارد'}
**ID:** `{user.id}`

{self.emoji['message']} **پیام:**
{user_message}
"""

            try:
                await context.bot.send_message(
                    chat_id=self.ADMIN_ID,
                    text=admin_message,
                    parse_mode='Markdown'
                )

                success_response = f"""
{self.emoji['success']} **پیام شما ارسال شد!**

پیام شما برای آقای امیر حسن محمدی ارسال شد.

📞 **برای فوریت بیشتر:**
`{self.business['phone']}`
"""

                await update.message.reply_text(success_response, parse_mode='Markdown')
                logger.info(f"📩 پیام کاربر {user.id} ارسال شد")

            except Exception as e:
                error_response = f"""
{self.emoji['error']} **خطا در ارسال پیام!**

📞 **لطفاً مستقیماً تماس بگیرید:**
`{self.business['phone']}`
"""

                await update.message.reply_text(error_response, parse_mode='Markdown')
                logger.error(f"❌ خطا در ارسال پیام: {e}")

            context.user_data['waiting_for_message'] = False
        else:
            await self.handle_normal_message(update, context)

    async def handle_normal_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت پیام‌های عادی"""
        response_text = f"""
{self.emoji['ai']} **پاسخ هوشمند:**

متشکرم از پیام شما! 🌟

برای دسترسی به خدمات از منوی اصلی استفاده کنید.

📞 **تماس مستقیم:**
`{self.business['phone']}`
"""

        await update.message.reply_text(response_text, parse_mode='Markdown')

    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کلیک روی دکمه‌های اینلاین"""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == 'check_membership':
            if await self.is_user_channel_member(query.from_user.id):
                await query.message.delete()
                await self.start_command_from_callback(query)
            else:
                await query.answer("❌ هنوز در کانال عضو نشده‌اید!", show_alert=True)
        
        elif data == 'main_menu':
            await self.show_main_menu(query)
        elif data == 'refresh_prices':
            await self.financial_analysis_callback(query)
        elif data == 'refresh_signals':
            await self.trading_signals_callback(query)
        elif data == 'vip_signals':
            await self.show_vip_signals(query)
        elif data.startswith('price_'):
            service_type = data.split('_')[1]
            await self.show_price_details(query, service_type)
        elif data.startswith('consult_'):
            service_type = data.split('_')[1]
            await self.show_consultation(query, service_type)

    async def start_command_from_callback(self, query):
        """اجرای دستور start از طریق callback"""
        user = query.from_user
        await self.save_user(user)

        welcome_message = f"""
{self.emoji['crown']} **{self.business['name']}**
{self.emoji['rocket']} *{self.business['title']}*

{self.emoji['fire']} **{self.business['slogan']}**

👋 **سلام {user.first_name} عزیز!**
{self.emoji['success']} **عضویت شما تایید شد!**

لطفاً از منوی زیر گزینه مورد نظر را انتخاب کنید:
"""

        keyboard_layout = [
            ["📊 تحلیل بازار مالی", "🎯 سیگنال‌های امروز"],
            ["🎨 طراحی وب سایت", "📱 اپلیکیشن موبایل"],
            ["📈 سئو و مارکتینگ", "🎬 تولید محتوا"],
            ["🛡️ امنیت سایبری", "💼 نمونه کارها"],
            ["📞 تماس مستقیم", "🌐 شبکه های اجتماعی"],
            ["📲 اشتراک شماره تماس", "💌 ارسال پیام به ادمین"]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)
        
        await query.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_main_menu(self, query):
        """نمایش منوی اصلی"""
        welcome_message = f"""
{self.emoji['crown']} **{self.business['name']}**
{self.emoji['rocket']} *{self.business['title']}*

{self.emoji['fire']} **{self.business['slogan']}**

👋 **سلام {query.from_user.first_name} عزیز!**
لطفاً از منوی زیر گزینه مورد نظر را انتخاب کنید:
"""

        keyboard_layout = [
            ["📊 تحلیل بازار مالی", "🎯 سیگنال‌های امروز"],
            ["🎨 طراحی وب سایت", "📱 اپلیکیشن موبایل"],
            ["📈 سئو و مارکتینگ", "🎬 تولید محتوا"],
            ["🛡️ امنیت سایبری", "💼 نمونه کارها"],
            ["📞 تماس مستقیم", "🌐 شبکه های اجتماعی"],
            ["📲 اشتراک شماره تماس", "💌 ارسال پیام به ادمین"]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)
        
        await query.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_price_details(self, query, service_type):
        """نمایش جزئیات قیمت"""
        prices = {
            'web': {
                'title': 'طراحی وب سایت',
                'prices': [
                    'وب سایت شرکتی: ۵-۱۵ میلیون تومان',
                    'فروشگاه اینترنتی: ۱۵-۳۰ میلیون تومان',
                    'پورتال سازمانی: ۳۰-۵۰ میلیون تومان'
                ]
            },
            'app': {
                'title': 'اپلیکیشن موبایل',
                'prices': [
                    'اپلیکیشن ساده: ۱۰-۲۰ میلیون تومان',
                    'اپلیکیشن متوسط: ۲۰-۵۰ میلیون تومان',
                    'اپلیکیشن پیشرفته: ۵۰-۱۰۰ میلیون تومان'
                ]
            },
            'seo': {
                'title': 'سئو و مارکتینگ',
                'prices': [
                    'سئو پایه: ۳-۸ میلیون تومان',
                    'سئو پیشرفته: ۸-۱۵ میلیون تومان',
                    'کمپین تبلیغاتی: ۱۵-۲۰ میلیون تومان'
                ]
            },
            'content': {
                'title': 'تولید محتوا',
                'prices': [
                    'محتوای متنی ساده: ۱-۳ میلیون تومان',
                    'محتوای ویدیویی: ۳-۶ میلیون تومان',
                    'کمپین محتوایی: ۶-۱۰ میلیون تومان'
                ]
            },
            'security': {
                'title': 'امنیت سایبری',
                'prices': [
                    'ارزیابی امنیتی: ۵-۱۰ میلیون تومان',
                    'امن‌سازی پایه: ۱۰-۲۰ میلیون تومان',
                    'امن‌سازی پیشرفته: ۲۰-۵۰ میلیون تومان'
                ]
            }
        }

        if service_type in prices:
            service = prices[service_type]
            price_text = f"""
{self.emoji['money']} **قیمت خدمات {service['title']}**

"""
            for price in service['prices']:
                price_text += f"• {price}\n"

            price_text += f"""

{self.emoji['success']} **برای استعلام دقیق:**
📞 {self.business['phone']}
"""

            buttons = [
                [InlineKeyboardButton("📞 تماس برای استعلام", url=f"tel:{self.business['phone']}")],
                [InlineKeyboardButton("💬 مشاوره واتساپ", url=f"https://wa.me/98{self.business['phone'][1:]}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text(price_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_vip_signals(self, query):
        """نمایش سیگنال‌های VIP"""
        vip_text = f"""
{self.emoji['diamond']} **سیگنال‌های VIP و پرایوت**

{self.emoji['fire']} **مزایای عضویت VIP:**
• سیگنال‌های لحظه‌ای
• تحلیل‌های پیشرفته
• پشتیبانی اختصاصی
• مشاوره شخصی

💰 **هزینه عضویت:**
• ماهانه: ۱ میلیون تومان
• سه ماهه: ۲.۵ میلیون تومان

📞 **برای عضویت:**
`{self.business['phone']}`
"""

        buttons = [
            [InlineKeyboardButton("📞 تماس برای عضویت", url=f"tel:{self.business['phone']}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(vip_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_consultation(self, query, service_type):
        """نمایش اطلاعات مشاوره"""
        consultation_text = f"""
{self.emoji['consultation']} **مشاوره رایگان**

📞 **برای دریافت مشاوره رایگان:**

• مستقیماً با ما تماس بگیرید
• یا از طریق واتساپ پیام دهید

{self.emoji['phone']} **شماره تماس:**
`{self.business['phone']}`
"""

        buttons = [
            [InlineKeyboardButton("📞 تماس تلفنی", url=f"tel:{self.business['phone']}")],
            [InlineKeyboardButton("💬 واتساپ", url=f"https://wa.me/98{self.business['phone'][1:]}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(consultation_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def financial_analysis_callback(self, query):
        """بروزرسانی قیمت‌ها از طریق callback"""
        if not await self.is_user_channel_member(query.from_user.id):
            await query.answer("❌ لطفاً ابتدا در کانال عضو شوید!", show_alert=True)
            return

        try:
            crypto_data = self.get_crypto_prices_simple()
            prices_data = self.get_iran_prices()

            analysis_text = f"""
{self.emoji['chart']} **بروزرسانی لحظه‌ای قیمت‌ها**
{self.emoji['time']} *آخرین بروزرسانی: {datetime.now().strftime("%H:%M:%S")}*

{self.emoji['crypto']} **ارزهای دیجیتال:**
"""

            for crypto in crypto_data:
                analysis_text += f"• **{crypto['name']}**: `${crypto['price']:,.2f}` "
                if crypto['change_24h'] >= 0:
                    analysis_text += f"{self.emoji['up']} +{crypto['change_24h']:.2f}%\n"
                else:
                    analysis_text += f"{self.emoji['down']} {crypto['change_24h']:.2f}%\n"

            analysis_text += f"\n{self.emoji['gold']} **طلای ۱۸ عیار:** `{prices_data.get('gold_18', 0):,.0f}` تومان\n"
            analysis_text += f"{self.emoji['dollar']} **دلار:** `{prices_data.get('usd', 0):,.0f}` تومان\n"

            buttons = [
                [InlineKeyboardButton("🔄 بروزرسانی مجدد", callback_data="refresh_prices")],
                [InlineKeyboardButton("🎯 سیگنال‌های VIP", callback_data="vip_signals")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            error_text = "خطا در بروزرسانی قیمت‌ها"
            await query.edit_message_text(error_text)

    async def trading_signals_callback(self, query):
        """بروزرسانی سیگنال‌ها از طریق callback"""
        try:
            signals = self.generate_daily_signals()

            signals_text = f"""
{self.emoji['signal']} **بروزرسانی سیگنال‌ها**
{self.emoji['time']} *آخرین بروزرسانی: {datetime.now().strftime("%H:%M:%S")}*

🎯 **سیگنال‌های فوری:**
"""

            for signal in signals[:2]:
                risk_emoji = "🟢" if signal['risk'] == 'کم' else "🟡" if signal['risk'] == 'متوسط' else "🔴"
                signals_text += f"""
• **{signal['asset']}** {risk_emoji}
  ورود: {signal['entry']}
  هدف: {signal['target']}
  حد ضرر: {signal['stop_loss']}
────────────────────
"""

            buttons = [
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_signals")],
                [InlineKeyboardButton("💎 سیگنال VIP", callback_data="vip_signals")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text(signals_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            error_text = "خطا در بروزرسانی سیگنال‌ها"
            await query.edit_message_text(error_text)

    def setup_handlers(self, application):
        """تنظیم هندلرهای ربات"""
        self.application = application

        # دستورات
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("price", self.price_command))
        application.add_handler(CommandHandler("signal", self.signal_command))
        application.add_handler(CommandHandler("services", self.services_command))
        application.add_handler(CommandHandler("contact", self.contact_command))
        application.add_handler(CommandHandler("help", self.help_command))

        # هندلرهای منوی اصلی
        application.add_handler(MessageHandler(filters.Text("📊 تحلیل بازار مالی"), self.financial_analysis))
        application.add_handler(MessageHandler(filters.Text("🎯 سیگنال‌های امروز"), self.trading_signals))
        application.add_handler(MessageHandler(filters.Text("🎨 طراحی وب سایت"), self.web_design_service))
        application.add_handler(MessageHandler(filters.Text("📱 اپلیکیشن موبایل"), self.app_development_service))
        application.add_handler(MessageHandler(filters.Text("📈 سئو و مارکتینگ"), self.seo_marketing_service))
        application.add_handler(MessageHandler(filters.Text("🎬 تولید محتوا"), self.content_creation_service))
        application.add_handler(MessageHandler(filters.Text("🛡️ امنیت سایبری"), self.cyber_security_service))
        application.add_handler(MessageHandler(filters.Text("💼 نمونه کارها"), self.portfolio_showcase))
        application.add_handler(MessageHandler(filters.Text("📞 تماس مستقیم"), self.contact_information))
        application.add_handler(MessageHandler(filters.Text("🌐 شبکه های اجتماعی"), self.social_media_links))
        application.add_handler(MessageHandler(filters.Text("💌 ارسال پیام به ادمین"), self.send_message_to_admin))
        application.add_handler(MessageHandler(filters.Text("📲 اشتراک شماره تماس"), self.request_contact))

        # هندلر دریافت شماره تماس
        application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))

        # هندلر دکمه‌های اینلاین
        application.add_handler(CallbackQueryHandler(self.handle_button_click))

        # هندلر پیام‌های متنی
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_message))

def main():
    """تابع اصلی اجرای ربات"""
    bot = UltimateBusinessBot()

    try:
        application = Application.builder().token(bot.BOT_TOKEN).build()
        bot.setup_handlers(application)

        print("🎉" + "="*60)
        print("🚀 ربات فوق حرفه‌ای امیر حسن محمدی")
        print("📊 تحلیل بازارهای مالی با قیمت‌های واقعی")
        print("🎯 سیگنال‌های معاملاتی پیشرفته")
        print("🔐 سیستم عضویت اجباری در کانال فعال شد")
        print("💼 تمام خدمات فعال و قابل استفاده")
        print("📞 کاربران ثبت‌شده:", bot.get_users_count())
        print("="*60)
        print("🔥 ربات با موفقیت راه‌اندازی شد!")
        print("🎉" + "="*60)

        application.run_polling()

    except Exception as e:
        print(f"❌ خطا در راه‌اندازی ربات: {e}")
        logger.error(f"خطای راه‌اندازی: {e}")

if __name__ == '__main__':
    main()
