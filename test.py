# auto_apply_jobs_multi_platform.py
# ===============================================
# Multi-Platform Job Search Dashboard
# (LinkedIn & Naukri) - Responsive Design
# ===============================================

from flask import Flask, render_template_string, request, redirect, url_for, flash
from playwright.sync_api import sync_playwright
import time, os, csv, json, webbrowser, random, threading
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.utils import secure_filename
from urllib.parse import urlencode, quote, urlparse, parse_qs

# ---------------- Configuration ----------------
SETTINGS_FILE = "settings.json"
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
LOG_FILE = "applied_jobs_log.csv"

# ---------------- Settings Management ----------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
    return {
        "LINKEDIN_EMAIL": "",
        "LINKEDIN_PASSWORD": "",
        "NAUKRI_EMAIL": "",
        "NAUKRI_PASSWORD": "",
        "RESUME_PATH": "",
        "LOCATION": "India",
        "KEYWORDS": "MIS Executive;Business Analyst",
        "APPLY_TITLE_KEYWORDS": "MIS;Business Analyst",
        "HEADLESS": False,
        "CHROME_PATH": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "USE_CHROME_PROFILE": True,
        "CHROME_PROFILE_PATH": "",
        "USE_REMOTE_DEBUGGING": False
    }

def save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------- Initialize ----------------
load_dotenv()
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

settings = load_settings()
LINKEDIN_EMAIL = settings.get("LINKEDIN_EMAIL") or os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = settings.get("LINKEDIN_PASSWORD") or os.getenv("LINKEDIN_PASSWORD", "")
NAUKRI_EMAIL = settings.get("NAUKRI_EMAIL") or os.getenv("NAUKRI_EMAIL", "")
NAUKRI_PASSWORD = settings.get("NAUKRI_PASSWORD") or os.getenv("NAUKRI_PASSWORD", "")
RESUME_PATH = settings.get("RESUME_PATH") or os.getenv("RESUME_PATH", "")
LOCATION = settings.get("LOCATION", "India")
KEYWORDS = settings.get("KEYWORDS", "MIS Executive;Business Analyst").split(";")
HEADLESS = settings.get("HEADLESS", False)

APPLY_TITLE_KEYWORDS = settings.get("APPLY_TITLE_KEYWORDS", "MIS;Business Analyst").split(";")
APPLY_TITLE_KEYWORDS = [k.strip().lower() for k in APPLY_TITLE_KEYWORDS if k.strip()]

CHROME_PATH = settings.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
USE_CHROME_PROFILE = settings.get("USE_CHROME_PROFILE", True)
CHROME_PROFILE_PATH = settings.get("CHROME_PROFILE_PATH", "")
USE_REMOTE_DEBUGGING = settings.get("USE_REMOTE_DEBUGGING", False)

# Initialize log file
if not Path(LOG_FILE).exists():
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Platform", "Keyword", "Location", "Job_Title", "Job_URL", "Status", "Timestamp"])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- Flask Setup ----------------
app = Flask(__name__)
app.secret_key = os.urandom(24)
jobs_cache = []

# Thread-local browser session
thread_local = threading.local()

def get_browser_session():
    """Get or create a thread-local browser session"""
    if not hasattr(thread_local, 'browser_session') or thread_local.browser_session['page'] is None:
        print("🔧 Creating new browser session for thread...")
        pw, browser, context, page = setup_browser()
        thread_local.browser_session = {
            'pw': pw,
            'browser': browser,
            'context': context,
            'page': page,
            'logged_in': {'linkedin': False, 'naukri': False}
        }
    return thread_local.browser_session['page']

def ensure_logged_in(platform='linkedin'):
    """Ensure the specified platform is logged in"""
    page = get_browser_session()
    
    if thread_local.browser_session['logged_in'].get(platform, False):
        try:
            # Check if still logged in
            if platform == 'linkedin':
                page.goto("https://www.linkedin.com/feed/", timeout=10000)
                if "feed" in page.url or "jobs" in page.url:
                    print(f"✅ Already logged in to {platform.title()}")
                    return page
            elif platform == 'naukri':
                page.goto("https://www.naukri.com/mnjuser/homepage", timeout=10000)
                current_url = page.url.lower()
                if "mnjuser" in current_url or "homepage" in current_url:
                    print(f"✅ Already logged in to {platform.title()}")
                    return page
                if page.locator('text="Complete profile"').count() > 0 or page.locator('text="My home"').count() > 0:
                    print(f"✅ Already logged in to {platform.title()}")
                    return page
            
            thread_local.browser_session['logged_in'][platform] = False
        except:
            thread_local.browser_session['logged_in'][platform] = False
    
    # Login if not logged in
    if platform == 'linkedin' and LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
        if login_linkedin(page, LINKEDIN_EMAIL, LINKEDIN_PASSWORD):
            thread_local.browser_session['logged_in'][platform] = True
            return page
    elif platform == 'naukri' and NAUKRI_EMAIL and NAUKRI_PASSWORD:
        if login_naukri(page, NAUKRI_EMAIL, NAUKRI_PASSWORD):
            thread_local.browser_session['logged_in'][platform] = True
            return page
    
    return None

def close_browser_session():
    """Close the thread-local browser session"""
    if hasattr(thread_local, 'browser_session'):
        session = thread_local.browser_session
        if session['context']:
            try:
                session['context'].close()
            except:
                pass
        if session['browser']:
            try:
                session['browser'].close()
            except:
                pass
        if session['pw']:
            try:
                session['pw'].stop()
            except:
                pass
        thread_local.browser_session = None

# ---------------- Browser Setup ----------------
def setup_browser(headless=None):
    global CHROME_PATH, USE_CHROME_PROFILE, CHROME_PROFILE_PATH, USE_REMOTE_DEBUGGING
    if headless is None:
        headless = HEADLESS
    
    pw = sync_playwright().start()
    
    # Find Chrome path
    chrome_path = CHROME_PATH
    if not chrome_path or not os.path.exists(chrome_path):
        common_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        for path in common_paths:
            if os.path.exists(path):
                chrome_path = path
                print(f"✅ Found Chrome at: {chrome_path}")
                break
    
    # Launch arguments
    launch_args = [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
    ]
    
    # Try to connect to existing Chrome with remote debugging
    if USE_REMOTE_DEBUGGING:
        try:
            print("🔍 Attempting to connect to existing Chrome instance (port 9222)...")
            browser = pw.chromium.connect_over_cdp("http://localhost:9222")
            if browser.contexts:
                context = browser.contexts[0]
                if context.pages:
                    page = context.pages[0]
                    print("✅ Connected to existing Chrome tab!")
                    return pw, browser, context, page
                else:
                    page = context.new_page()
                    print("✅ Connected to existing Chrome, created new tab!")
                    return pw, browser, context, page
            else:
                context = browser.new_context(viewport={'width': 1920, 'height': 1080})
                page = context.new_page()
                print("✅ Connected to existing Chrome instance!")
                return pw, browser, context, page
        except Exception as e:
            print(f"ℹ️ Could not connect to existing Chrome: {e}")
            print("🚀 Launching new Chrome instance...")
    
    # Launch with Chrome profile
    if chrome_path and os.path.exists(chrome_path):
        if USE_CHROME_PROFILE and CHROME_PROFILE_PATH and os.path.exists(CHROME_PROFILE_PATH):
            print(f"👤 Using Chrome profile from: {CHROME_PROFILE_PATH}")
            try:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=CHROME_PROFILE_PATH,
                    headless=headless,
                    executable_path=chrome_path,
                    args=launch_args,
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.pages[0] if context.pages else context.new_page()
                print("✅ Chrome profile loaded successfully!")
                return pw, None, context, page
            except Exception as e:
                print(f"⚠️ Failed to load Chrome profile: {e}")
        
        print(f"🚀 Launching Chrome from: {chrome_path}")
        browser = pw.chromium.launch(
            headless=headless,
            executable_path=chrome_path,
            args=launch_args
        )
    else:
        print("⚠️ Chrome not found, using Playwright's built-in Chromium")
        browser = pw.chromium.launch(headless=headless, args=launch_args)
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = context.new_page()
    return pw, browser, context, page

# ---------------- Login Functions ----------------
def login_linkedin(page, email, password):
    if not email or not password:
        print("⚠️ LinkedIn credentials not provided")
        return False
    try:
        print("🔐 Logging into LinkedIn...")
        page.goto("https://www.linkedin.com/login", timeout=60000)
        page.wait_for_selector("input#username", timeout=10000)
        page.fill("input#username", email)
        page.fill("input#password", password)
        time.sleep(1 + random.random())
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2 + random.random())
        if "feed" in page.url or "jobs" in page.url:
            print("✅ LinkedIn login successful")
            return True
        else:
            print("⚠️ LinkedIn login may have failed")
            return False
    except Exception as e:
        print(f"❌ LinkedIn login error: {e}")
        return False

def login_naukri(page, email, password):
    if not email or not password:
        print("⚠️ Naukri credentials not provided")
        return False
    try:
        print("🔐 Logging into Naukri...")
        page.goto("https://www.naukri.com/nlogin/login", timeout=60000)
        page.wait_for_selector("input#usernameField", timeout=10000)
        page.fill("input#usernameField", email)
        page.fill("input#passwordField", password)
        time.sleep(1 + random.random())
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3 + random.random())
        
        current_url = page.url.lower()
        if "mnjuser" in current_url or "homepage" in current_url or "naukri.com" in current_url:
            try:
                profile_indicators = [
                    'text="Complete profile"',
                    'text="Profile performance"',
                    'text="My home"',
                    'a[href*="mnjuser"]',
                    'div:has-text("Profile")'
                ]
                
                for indicator in profile_indicators:
                    if page.locator(indicator).count() > 0:
                        print("✅ Naukri login successful")
                        return True
                
                if "naukri.com" in current_url and "login" not in current_url:
                    print("✅ Naukri login successful")
                    return True
                    
            except:
                pass
        
        print("⚠️ Naukri login may have failed - please check credentials")
        return False
    except Exception as e:
        print(f"❌ Naukri login error: {e}")
        return False

# ---------------- Job Search Functions ----------------
def build_linkedin_all_jobs_url(keyword: str, location: str) -> str:
    """Build LinkedIn URL for ALL jobs"""
    params = {
        "keywords": keyword,
        "location": location,
        "f_TPR": "r86400",
        "sortBy": "DD",
        "position": "1",
        "pageNum": "0"
    }
    return f"https://www.linkedin.com/jobs/search/?{urlencode(params, quote_via=quote)}"

def build_naukri_url(keyword: str, location: str) -> str:
    keyword_formatted = keyword.replace(" ", "-")
    location_formatted = location.replace(" ", "-").lower()
    return f"https://www.naukri.com/{keyword_formatted}-jobs-in-{location_formatted}"

def fetch_linkedin_jobs(page, keyword, location):
    """Fetch ALL LinkedIn jobs with matching keywords"""
    print(f"\n🔍 [LinkedIn] Searching: '{keyword}' in '{location}'")
    
    url = build_linkedin_all_jobs_url(keyword, location)
    
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(4 + random.random())

        job_card_selectors = [
            'li.jobs-search-results__list-item',
            'li.scaffold-layout__list-item',
            'div.job-card-container'
        ]
        
        job_cards = []
        for sel in job_card_selectors:
            try:
                cards = page.locator(sel).all()
                if len(cards) > 0:
                    job_cards = cards
                    print(f"✅ Found {len(job_cards)} LinkedIn job cards")
                    break
            except:
                continue
        
        if not job_cards:
            print("❌ No LinkedIn job cards found")
            return []

        results = []
        for card in job_cards[:50]:
            try:
                title_link = card.locator('a.job-card-list__title, a[href*="/jobs/view/"]').first
                title = title_link.inner_text().strip()
                href = title_link.get_attribute("href")
                
                if not href or not title:
                    continue
                
                if not href.startswith("http"):
                    href = "https://www.linkedin.com" + href
                
                if "?" in href:
                    href = href.split("?")[0]

                if APPLY_TITLE_KEYWORDS:
                    if not any(kw.lower() in title.lower() for kw in APPLY_TITLE_KEYWORDS):
                        continue

                is_easy_apply = card.locator('span:has-text("Easy Apply")').count() > 0
                
                results.append({
                    "platform": "LinkedIn",
                    "keyword": keyword,
                    "title": title,
                    "url": href,
                    "easy_apply": is_easy_apply
                })
                
            except Exception as e:
                continue

        print(f"✅ Found {len(results)} LinkedIn jobs matching criteria")
        return results
        
    except Exception as e:
        print(f"❌ Error fetching LinkedIn jobs: {e}")
        return []

def fetch_naukri_jobs(page, keyword, location):
    print(f"\n🔍 [Naukri] Searching: '{keyword}' in '{location}'")
    url = build_naukri_url(keyword, location)
    
    try:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3 + random.random())

        for i in range(5):
            page.keyboard.press("End")
            time.sleep(1)

        job_cards = page.locator('article.jobTuple, div.srp-jobtuple-wrapper').all()
        
        if not job_cards:
            print("❌ No Naukri job cards found")
            return []

        print(f"✅ Found {len(job_cards)} Naukri job cards")
        results = []
        
        for card in job_cards[:50]:
            try:
                title_elem = card.locator('a.title, a.heading-span').first
                title = title_elem.inner_text().strip()
                href = title_elem.get_attribute("href")
                
                if not href or not title:
                    continue
                
                if not href.startswith("http"):
                    href = "https://www.naukri.com" + href

                if APPLY_TITLE_KEYWORDS:
                    if not any(kw.lower() in title.lower() for kw in APPLY_TITLE_KEYWORDS):
                        continue

                results.append({
                    "platform": "Naukri",
                    "keyword": keyword,
                    "title": title,
                    "url": href
                })
                
            except Exception as e:
                continue

        print(f"✅ Found {len(results)} Naukri jobs matching criteria")
        return results
        
    except Exception as e:
        print(f"❌ Error fetching Naukri jobs: {e}")
        return []

def log_application(platform, keyword, location, title, url, status):
    try:
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                platform, keyword, location, title, url, status,
                time.strftime("%Y-%m-%d %H:%M:%S")
            ])
    except Exception as e:
        print(f"⚠️ Failed to log application: {e}")

# ---------------- Flask Templates with Responsive Design ----------------
home_template = """
<!doctype html>
<html>
<head>
    <meta charset='utf-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Job Search Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 10px;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        /* Header */
        .header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 20px;
            border-bottom: 2px solid #0a66c2;
            flex-wrap: wrap;
            gap: 10px;
        }
        h2 { color: #0a66c2; font-size: 24px; }
        
        .header-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .settings-link, .close-browser { 
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 500;
            display: inline-block;
            text-align: center;
            white-space: nowrap;
        }
        .settings-link { 
            background: #0a66c2; 
            color: white;
        }
        .close-browser { 
            background: #dc3545; 
            color: white;
        }
        
        /* Search Form */
        .search-form { 
            background: #f8f9fa;
            padding: 20px;
            margin: 20px;
            border-radius: 8px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        .search-form input, .search-form select { 
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .search-form button { 
            width: 100%;
            padding: 12px;
            background: #0a66c2;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 10px;
        }
        .search-form button:active {
            background: #084d8f;
        }
        
        /* Status Messages */
        .status { 
            padding: 15px;
            margin: 20px;
            border-radius: 5px;
            font-weight: 500;
        }
        .status.success { 
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error { 
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        /* Jobs Section */
        .jobs-section {
            padding: 20px;
        }
        .jobs-header {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .jobs-header h3 {
            color: #333;
            font-size: 20px;
        }
        
        /* Job Cards for Mobile */
        .job-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .job-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
            gap: 10px;
        }
        .job-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            line-height: 1.4;
            flex: 1;
        }
        .job-title a {
            color: #0a66c2;
            text-decoration: none;
        }
        .job-title a:active {
            color: #084d8f;
        }
        .job-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }
        .platform-badge { 
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            white-space: nowrap;
        }
        .badge-linkedin { background: #0a66c2; color: white; }
        .badge-naukri { background: #1b7ea8; color: white; }
        .easy-apply-tag { 
            background: #10b981;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            white-space: nowrap;
        }
        .keyword-tag {
            background: #e0e0e0;
            color: #333;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .apply-btn { 
            width: 100%;
            background: #057642;
            color: white;
            padding: 10px;
            text-decoration: none;
            border-radius: 5px;
            display: block;
            text-align: center;
            font-weight: 600;
        }
        .apply-btn:active {
            background: #046535;
        }
        
        /* Desktop Table (hidden on mobile) */
        .desktop-table {
            display: none;
        }
        table { 
            width: 100%;
            border-collapse: collapse;
        }
        th, td { 
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th { 
            background: #0a66c2;
            color: white;
            font-weight: 600;
        }
        td a { 
            color: #0a66c2;
            text-decoration: none;
        }
        td a:hover {
            text-decoration: underline;
        }
        .table-apply-btn {
            background: #057642;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            display: inline-block;
            white-space: nowrap;
        }
        .table-apply-btn:hover {
            background: #046535;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #666;
        }
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        /* Desktop Styles */
        @media (min-width: 768px) {
            body { padding: 20px; }
            h2 { font-size: 28px; }
            
            .search-form {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                align-items: end;
            }
            .form-group {
                margin-bottom: 0;
            }
            .search-form button {
                width: auto;
                margin-top: 0;
            }
            
            /* Hide mobile cards, show table */
            .mobile-cards { display: none; }
            .desktop-table { display: block; }
            
            .settings-link, .close-browser {
                padding: 10px 20px;
            }
        }
        
        @media (min-width: 1024px) {
            .search-form {
                grid-template-columns: 1fr 1fr 2fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚀 Job Search Dashboard</h2>
            <div class="header-buttons">
                <a href='/close-browser' class='close-browser' onclick="return confirm('Close browser session?')">🔴 Close Browser</a>
                <a href='/settings' class='settings-link'>⚙️ Settings</a>
            </div>
        </div>
        
        {% if status %}
        <div class="status {{ 'success' if 'success' in status.lower() or '✅' in status else 'error' }}">{{ status }}</div>
        {% endif %}
        
        {% if linkedin_configured and naukri_configured %}
        <div class="status success">
            ✅ <strong>Ready to Go!</strong> Both LinkedIn and Naukri are configured. You can search jobs on all platforms.
        </div>
        {% elif linkedin_configured %}
        <div class="status success">
            ✅ <strong>LinkedIn Configured:</strong> You can search LinkedIn jobs. 
            <a href="/settings" style="color: #155724; text-decoration: underline; font-weight: bold;">Add Naukri credentials</a> to search on both platforms.
        </div>
        {% elif naukri_configured %}
        <div class="status success">
            ✅ <strong>Naukri Configured:</strong> You can search Naukri jobs. 
            <a href="/settings" style="color: #155724; text-decoration: underline; font-weight: bold;">Add LinkedIn credentials</a> to search on both platforms.
        </div>
        {% else %}
        <div class="status error">
            ⚠️ <strong>Setup Required:</strong> Please configure your LinkedIn and Naukri credentials in <a href="/settings" style="color: #721c24; text-decoration: underline; font-weight: bold;">Settings</a> before searching for jobs.
        </div>
        {% endif %}
        
        <div class="search-form">
            <form action='/fetch' method='post'>
                <div class="form-group">
                    <label>Platform:</label>
                    <select name='platform' required>
                        <option value='all'>All Platforms</option>
                        <option value='linkedin'>LinkedIn</option>
                        <option value='naukri'>Naukri</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Keyword:</label>
                    <input name='keyword' value='{{keyword}}' required placeholder="e.g., MIS Executive">
                </div>
                
                <div class="form-group">
                    <label>Location:</label>
                    <input name='location' value='{{location}}' required placeholder="e.g., India">
                </div>
                
                <button type='submit'>🔍 Search Jobs</button>
            </form>
        </div>
        
        {% if jobs %}
        <div class="jobs-section">
            <div class="jobs-header">
                <h3>Found {{ jobs|length }} Jobs</h3>
            </div>
            
            <!-- Mobile Card View -->
            <div class="mobile-cards">
                {% for j in jobs %}
                <div class="job-card">
                    <div class="job-card-header">
                        <div class="job-title">
                            <a href="{{j.url}}" target="_blank">{{j.title}}</a>
                        </div>
                    </div>
                    <div class="job-meta">
                        <span class="platform-badge badge-{{ j.platform.lower() }}">{{ j.platform }}</span>
                        {% if j.get('easy_apply') %}
                        <span class="easy-apply-tag">Easy Apply</span>
                        {% endif %}
                        <span class="keyword-tag">{{j.keyword}}</span>
                    </div>
                    <a class="apply-btn" href='{{j.url}}' target='_blank'>📝 Apply Now</a>
                </div>
                {% endfor %}
            </div>
            
            <!-- Desktop Table View -->
            <div class="desktop-table">
                <table>
                    <tr>
                        <th>Platform</th>
                        <th>Job Title</th>
                        <th>Keyword</th>
                        <th>Action</th>
                    </tr>
                    {% for j in jobs %}
                    <tr>
                        <td>
                            <span class="platform-badge badge-{{ j.platform.lower() }}">{{ j.platform }}</span>
                            {% if j.get('easy_apply') %}
                            <span class="easy-apply-tag">Easy Apply</span>
                            {% endif %}
                        </td>
                        <td><a href="{{j.url}}" target="_blank">{{j.title}}</a></td>
                        <td>{{j.keyword}}</td>
                        <td>
                            <a class="table-apply-btn" href='{{j.url}}' target='_blank'>📝 Apply</a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        {% else %}
        <div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <h3>No jobs found yet</h3>
            <p>Use the search form above to find jobs</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

settings_template = r"""
<!doctype html>
<html>
<head>
    <meta charset='utf-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Settings - Job Search Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 10px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 20px;
        }
        
        h2 { 
            color: #0a66c2;
            margin-bottom: 15px;
            font-size: 24px;
        }
        h3 { 
            color: #333;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #0a66c2;
            font-size: 18px;
        }
        h4 {
            color: #0a66c2;
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        .back-link { 
            display: inline-block;
            margin: 10px 0 20px;
            color: #0a66c2;
            text-decoration: none;
            font-weight: 500;
        }
        .back-link:active {
            color: #084d8f;
        }
        
        form { 
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }
        
        label { 
            display: block;
            margin: 15px 0 5px;
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }
        
        input[type="text"], 
        input[type="password"], 
        input[type="file"], 
        textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            font-family: inherit;
        }
        
        textarea { 
            resize: vertical;
            min-height: 80px;
        }
        
        input[type="checkbox"] { 
            margin-right: 8px;
            width: 18px;
            height: 18px;
            vertical-align: middle;
        }
        
        .checkbox-label {
            display: flex;
            align-items: center;
            margin: 15px 0;
            font-weight: 500;
            cursor: pointer;
        }
        
        button { 
            width: 100%;
            margin-top: 20px;
            padding: 12px;
            background: #0a66c2;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
        }
        button:active {
            background: #084d8f;
        }
        
        .info { 
            background: #d1ecf1;
            padding: 12px;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 14px;
            border-left: 4px solid #0a66c2;
        }
        
        .status { 
            padding: 15px;
            margin: 0 0 20px;
            border-radius: 5px;
            font-weight: 500;
        }
        .status.success { 
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        small { 
            display: block;
            color: #666;
            margin-top: 5px;
            font-size: 12px;
            line-height: 1.4;
        }
        
        .platform-section { 
            background: #fff;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #0a66c2;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* Desktop styles */
        @media (min-width: 768px) {
            body { padding: 20px; }
            .container { padding: 30px; }
            h2 { font-size: 28px; }
            h3 { font-size: 20px; }
            
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }
            .form-row label {
                margin-top: 0;
            }
            
            button {
                width: auto;
                min-width: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚙️ Settings</h2>
        <a href="/" class="back-link">← Back to Dashboard</a>
        
        {% if status %}
        <div class="status success">{{ status }}</div>
        {% endif %}
        
        <form method='post' enctype='multipart/form-data'>
            <h3>📧 Platform Credentials</h3>
            
            <div class="platform-section">
                <h4>LinkedIn</h4>
                <label>Email:</label>
                <input type="text" name='LINKEDIN_EMAIL' value='{{ s["LINKEDIN_EMAIL"] }}' placeholder="your.email@example.com">
                <label>Password:</label>
                <input type='password' name='LINKEDIN_PASSWORD' value='{{ s["LINKEDIN_PASSWORD"] }}' placeholder="••••••••">
            </div>
            
            <div class="platform-section">
                <h4>Naukri</h4>
                <label>Email:</label>
                <input type="text" name='NAUKRI_EMAIL' value='{{ s["NAUKRI_EMAIL"] }}' placeholder="your.email@example.com">
                <label>Password:</label>
                <input type='password' name='NAUKRI_PASSWORD' value='{{ s["NAUKRI_PASSWORD"] }}' placeholder="••••••••">
            </div>
            
            <h3>📄 Resume</h3>
            <label>Upload Resume (PDF, DOC, DOCX):</label>
            <input type='file' name='resume' accept='.pdf,.doc,.docx'>
            {% if s["RESUME_PATH"] %}
            <div class="info">✅ Current Resume: {{ s["RESUME_PATH"] }}</div>
            {% endif %}
            
            <h3>🔍 Search Preferences</h3>
            <label>Default Location:</label>
            <input type="text" name='LOCATION' value='{{ s["LOCATION"] }}' placeholder="India">
            
            <label>Keywords (semicolon separated):</label>
            <textarea name='KEYWORDS' placeholder="MIS Executive;Business Analyst;Data Analyst">{{ s["KEYWORDS"] }}</textarea>
            <small>Example: MIS Executive;Business Analyst;Data Analyst</small>
            
            <label>Title Filter Keywords (semicolon separated):</label>
            <textarea name='APPLY_TITLE_KEYWORDS' placeholder="MIS;Business Analyst">{{ s["APPLY_TITLE_KEYWORDS"] }}</textarea>
            <small>Only show jobs with titles containing these keywords. Leave empty to show all.</small>
            
            <h3>🌐 Chrome Settings</h3>
            <label class="checkbox-label">
                <input type='checkbox' name='USE_CHROME_PROFILE' value='true' {% if s.get("USE_CHROME_PROFILE") %}checked{% endif %}>
                Use existing Chrome profile (stay logged in)
            </label>
            
            <label>Chrome Profile Path:</label>
            <input type="text" name='CHROME_PROFILE_PATH' value='{{ s.get("CHROME_PROFILE_PATH", "") }}' placeholder='C:\Users\YourName\AppData\Local\Google\Chrome\User Data'>
            
            <label>Chrome Executable Path:</label>
            <input type="text" name='CHROME_PATH' value='{{ s.get("CHROME_PATH", "") }}' placeholder='C:\Program Files\Google\Chrome\Application\chrome.exe'>
            
            <label class="checkbox-label">
                <input type='checkbox' name='USE_REMOTE_DEBUGGING' value='true' {% if s.get("USE_REMOTE_DEBUGGING") %}checked{% endif %}>
                Connect to existing Chrome window (Advanced)
            </label>
            
            <label class="checkbox-label">
                <input type='checkbox' name='HEADLESS' value='true' {% if s.get("HEADLESS") %}checked{% endif %}>
                Run browser in headless mode (invisible)
            </label>
            
            <button type='submit'>💾 Save Settings</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    status = request.args.get("status", "")
    keyword = KEYWORDS[0] if KEYWORDS else ""
    return render_template_string(
        home_template,
        jobs=jobs_cache,
        keyword=keyword,
        location=LOCATION,
        status=status
    )

@app.route("/fetch", methods=["POST"])
def fetch():
    platform = request.form.get("platform", "all").strip().lower()
    keyword = request.form.get("keyword", "").strip()
    location = request.form.get("location", "").strip()
    
    if not keyword or not location:
        return redirect(url_for("index", status="❌ Please provide both keyword and location"))
    
    global jobs_cache
    jobs_cache = []
    
    try:
        if platform == "all" or platform == "linkedin":
            if LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
                page = ensure_logged_in('linkedin')
                if page:
                    jobs_cache.extend(fetch_linkedin_jobs(page, keyword, location))
            else:
                print("⚠️ LinkedIn credentials not configured")
        
        if platform == "all" or platform == "naukri":
            if NAUKRI_EMAIL and NAUKRI_PASSWORD:
                page = ensure_logged_in('naukri')
                if page:
                    jobs_cache.extend(fetch_naukri_jobs(page, keyword, location))
            else:
                print("⚠️ Naukri credentials not configured")
        
        status = f"✅ Found {len(jobs_cache)} jobs!" if jobs_cache else "❌ No jobs found"
        
    except Exception as e:
        status = f"❌ Error: {str(e)}"
        jobs_cache = []
    
    return redirect(url_for("index", status=status))

@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "POST":
        current_settings = load_settings()
        
        current_settings["LINKEDIN_EMAIL"] = request.form.get("LINKEDIN_EMAIL", "").strip()
        current_settings["LINKEDIN_PASSWORD"] = request.form.get("LINKEDIN_PASSWORD", "").strip()
        current_settings["NAUKRI_EMAIL"] = request.form.get("NAUKRI_EMAIL", "").strip()
        current_settings["NAUKRI_PASSWORD"] = request.form.get("NAUKRI_PASSWORD", "").strip()
        current_settings["LOCATION"] = request.form.get("LOCATION", "India").strip()
        current_settings["KEYWORDS"] = request.form.get("KEYWORDS", "").strip()
        current_settings["APPLY_TITLE_KEYWORDS"] = request.form.get("APPLY_TITLE_KEYWORDS", "").strip()
        current_settings["HEADLESS"] = request.form.get("HEADLESS") == "true"
        current_settings["USE_CHROME_PROFILE"] = request.form.get("USE_CHROME_PROFILE") == "true"
        current_settings["CHROME_PROFILE_PATH"] = request.form.get("CHROME_PROFILE_PATH", "").strip()
        current_settings["CHROME_PATH"] = request.form.get("CHROME_PATH", "").strip()
        current_settings["USE_REMOTE_DEBUGGING"] = request.form.get("USE_REMOTE_DEBUGGING") == "true"
        
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                current_settings["RESUME_PATH"] = file_path
        
        save_settings(current_settings)
        
        global LINKEDIN_EMAIL, LINKEDIN_PASSWORD, NAUKRI_EMAIL, NAUKRI_PASSWORD
        global RESUME_PATH, LOCATION, KEYWORDS, APPLY_TITLE_KEYWORDS, HEADLESS
        global USE_CHROME_PROFILE, CHROME_PROFILE_PATH, CHROME_PATH, USE_REMOTE_DEBUGGING
        
        LINKEDIN_EMAIL = current_settings["LINKEDIN_EMAIL"]
        LINKEDIN_PASSWORD = current_settings["LINKEDIN_PASSWORD"]
        NAUKRI_EMAIL = current_settings["NAUKRI_EMAIL"]
        NAUKRI_PASSWORD = current_settings["NAUKRI_PASSWORD"]
        RESUME_PATH = current_settings["RESUME_PATH"]
        LOCATION = current_settings["LOCATION"]
        KEYWORDS = current_settings["KEYWORDS"].split(";")
        APPLY_TITLE_KEYWORDS = [k.strip().lower() for k in current_settings["APPLY_TITLE_KEYWORDS"].split(";") if k.strip()]
        HEADLESS = current_settings["HEADLESS"]
        USE_CHROME_PROFILE = current_settings["USE_CHROME_PROFILE"]
        CHROME_PROFILE_PATH = current_settings["CHROME_PROFILE_PATH"]
        CHROME_PATH = current_settings["CHROME_PATH"]
        USE_REMOTE_DEBUGGING = current_settings["USE_REMOTE_DEBUGGING"]
        
        close_browser_session()
        
        return redirect(url_for("settings_page", status="✅ Settings saved successfully!"))
    
    s = load_settings()
    status = request.args.get("status", "")
    return render_template_string(settings_template, s=s, status=status)

@app.route("/close-browser")
def close_browser():
    """Manually close the browser session"""
    close_browser_session()
    return redirect(url_for("index", status="✅ Browser session closed"))

# ---------------- Main ----------------
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Job Search Dashboard (LinkedIn & Naukri)")
    print("=" * 60)
    print("🌐 Starting server at http://127.0.0.1:5000")
    print("💡 Supported platforms: LinkedIn, Naukri")
    print("📱 Responsive design: Works on PC and Mobile")
    print("=" * 60)
    
    webbrowser.open("http://127.0.0.1:5000", new=2)
    
    try:
        app.run(debug=False, port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        close_browser_session()
        print("✅ Browser closed. Bye!")