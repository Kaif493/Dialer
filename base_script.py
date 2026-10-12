import os
import re
import time
import random
import threading
import json
from zoneinfo import ZoneInfo
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from colorama import init, Fore, Style


# ============================================================
# TIMEZONE
# ============================================================

INDIA_TZ = ZoneInfo("Asia/Kolkata")


# ============================================================
# COLORAMA
# ============================================================

init(autoreset=True)


# ============================================================
# CONFIGURATION
# ============================================================

# BASE_URL = "--https://affiliate.abc.abc--"
# LOGIN_URL = f"{BASE_URL}/login"

# AFFILIATE_ACCOUNTS_URL = (
#     "https://admin-api.robuzz.lol/"
#     "marketing/v1/affiliate-accounts/"
# )

# REPORT_URL = (
#     "https://admin-reporting.robuzz.lol/"
#     "reports/v2/affiliate-report/users"
# )

OUTPUT_PATH = r"---"

STATE_FILE = os.path.join(
    OUTPUT_PATH,
    "affiliate_signup_counts.json"
)

# Fixed output file name
OUTPUT_FILENAME = "xyz.csv"

# Suffix added to the affiliate name to build "Lead Source 2"
LEAD_SOURCE_SUFFIX = "_Auto"
USERNAME = "-username-"
PASSWORD = "--password--"
MASTER_AFFILIATE_ID = "--master-affiliate-id--"


# ============================================================
# API SETTINGS
# ============================================================

PAGE_SIZE = 100
DISCOVERY_PAGE_SIZE = 600
DISCOVERY_DELAY = (0.2, 0.5)
MAX_RETRIES = 3
DELAY_API_CALLS = (2.0, 4.0)
DELAY_AFFILIATE_SWITCH = (3.0, 6.0)
DELAY_AFTER_LOGIN = (2.0, 4.0)
DEFAULT_RATE_LIMIT_WAIT = 30


# ============================================================
# TERMINAL LOCK
# ============================================================

LOCK = threading.Lock()


# ============================================================
# LOGGING
# ============================================================

def log(message, color=""):

    timestamp = datetime.now(INDIA_TZ).strftime("%H:%M:%S")

    with LOCK:

        print(
            f"{Style.DIM}{timestamp}{Style.RESET_ALL}  "
            f"{color}{message}{Style.RESET_ALL}"
        )


def log_banner(text):

    border = "=" * 70

    with LOCK:

        print()

        print(f"{Fore.CYAN}{Style.BRIGHT}{border}{Style.RESET_ALL}")

        print(
            f"{Fore.CYAN}{Style.BRIGHT}"
            f"{text.center(70)}"
            f"{Style.RESET_ALL}"
        )

        print(f"{Fore.CYAN}{Style.BRIGHT}{border}{Style.RESET_ALL}")

        print()


def random_pause(minimum, maximum):

    time.sleep(random.uniform(minimum, maximum))


# ============================================================
# VALIDATE CONFIG
# ============================================================

def validate_config():

    if not USERNAME:

        raise RuntimeError(
            "WFIX_USERNAME environment variable is missing."
        )

    if not PASSWORD:

        raise RuntimeError(
            "WFIX_PASSWORD environment variable is missing."
        )

    if not MASTER_AFFILIATE_ID:

        raise RuntimeError(
            "MASTER_AFFILIATE_ID is missing."
        )


# ============================================================
# SELENIUM DRIVER
# ============================================================

def get_driver():

    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)

    return driver


# ============================================================
# FIND LOGIN INPUT
# ============================================================

def find_username_field(driver, timeout=45):

    wait = WebDriverWait(driver, timeout)

    selectors = [
        (By.CSS_SELECTOR, 'input[type="text"]'),
        (By.CSS_SELECTOR, 'input[type="email"]'),
        (By.CSS_SELECTOR, 'input[name="username"]'),
        (By.CSS_SELECTOR, 'input[name="userName"]'),
        (By.CSS_SELECTOR, 'input[autocomplete="username"]'),
        (By.CSS_SELECTOR, 'input[placeholder*="user" i]'),
        (By.CSS_SELECTOR, 'input[placeholder*="email" i]'),
        (By.XPATH, '//input[contains(@id,"user")]'),
        (By.XPATH, '//input[contains(@name,"user")]'),
        (By.XPATH, '//*[@id="root"]//form//input[1]'),
    ]

    last_error = None

    for locator in selectors:

        try:

            field = wait.until(
                EC.presence_of_element_located(locator)
            )

            if field.is_displayed():

                return field

        except Exception as e:

            last_error = e

    raise RuntimeError(
        "Could not find username field on login page. "
        f"Current URL: {driver.current_url}. "
        f"Last error: {last_error}"
    )


# ============================================================
# FIND PASSWORD INPUT
# ============================================================

def find_password_field(driver, timeout=45):

    wait = WebDriverWait(driver, timeout)

    selectors = [
        (By.CSS_SELECTOR, 'input[type="password"]'),
        (By.CSS_SELECTOR, 'input[name="password"]'),
        (By.CSS_SELECTOR, 'input[autocomplete="current-password"]'),
        (By.XPATH, '//*[@id="standard-adornment-password"]'),
        (By.XPATH, '//input[contains(@id,"password")]'),
    ]

    last_error = None

    for locator in selectors:

        try:

            field = wait.until(
                EC.presence_of_element_located(locator)
            )

            if field.is_displayed():

                return field

        except Exception as e:

            last_error = e

    raise RuntimeError(
        "Could not find password field on login page. "
        f"Current URL: {driver.current_url}. "
        f"Last error: {last_error}"
    )


# ============================================================
# FIND SUBMIT BUTTON
# ============================================================

def find_submit_button(driver, timeout=45):

    wait = WebDriverWait(driver, timeout)

    selectors = [
        (By.CSS_SELECTOR, 'button[type="submit"]'),
        (By.XPATH, '//form//button[@type="submit"]'),
        (
            By.XPATH,
            '//button[contains(translate(normalize-space(.), '
            '"ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
            '"abcdefghijklmnopqrstuvwxyz"),'
            '"login")]'
        ),
        (
            By.XPATH,
            '//button[contains(translate(normalize-space(.), '
            '"ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
            '"abcdefghijklmnopqrstuvwxyz"),'
            '"sign in")]'
        ),
        (By.XPATH, '//*[@id="root"]//form//button'),
    ]

    last_error = None

    for locator in selectors:

        try:

            button = wait.until(
                EC.element_to_be_clickable(locator)
            )

            if button.is_displayed():

                return button

        except Exception as e:

            last_error = e

    raise RuntimeError(
        "Could not find login submit button. "
        f"Current URL: {driver.current_url}. "
        f"Last error: {last_error}"
    )


# ============================================================
# LOGIN
# ============================================================

def do_login():

    log("Opening affiliate login page...", Fore.CYAN)

    driver = get_driver()

    try:

        driver.get(LOGIN_URL)

        log(f"Login page loaded: {driver.current_url}", Style.DIM)

        # ----------------------------------------------------
        # Wait for page DOM
        # ----------------------------------------------------

        WebDriverWait(driver, 45).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) in ("interactive", "complete")
        )

        random_pause(1.0, 2.0)

        # ----------------------------------------------------
        # USERNAME
        # ----------------------------------------------------

        username_field = find_username_field(driver, 45)

        log("Username field detected.", Style.DIM)

        username_field.clear()
        username_field.send_keys(USERNAME)

        # ----------------------------------------------------
        # PASSWORD
        # ----------------------------------------------------

        password_field = find_password_field(driver, 45)

        log("Password field detected.", Style.DIM)

        password_field.clear()
        password_field.send_keys(PASSWORD)

        # ----------------------------------------------------
        # SUBMIT
        # ----------------------------------------------------

        submit_btn = find_submit_button(driver, 45)

        log("Login button detected.", Style.DIM)

        submit_btn.click()

        log(
            "Login submitted; waiting for authentication...",
            Fore.CYAN
        )

        # ----------------------------------------------------
        # WAIT FOR REDIRECT
        # ----------------------------------------------------

        try:

            WebDriverWait(driver, 45).until(
                lambda d: d.current_url.rstrip("/")
                != LOGIN_URL.rstrip("/")
            )

        except Exception:

            # Some applications authenticate without changing
            # the URL immediately. Give the page more time.

            random_pause(3.0, 5.0)

        # ----------------------------------------------------
        # WAIT AFTER LOGIN
        # ----------------------------------------------------

        random_pause(*DELAY_AFTER_LOGIN)

        log(f"Post-login URL: {driver.current_url}", Style.DIM)

        # ----------------------------------------------------
        # SEARCH STORAGE FOR TOKEN
        # ----------------------------------------------------

        jwt_token = None

        for storage_name in ("localStorage", "sessionStorage"):

            try:

                storage = driver.execute_script(
                    f"""
                    return Object.fromEntries(
                        Object.entries(
                            window.{storage_name}
                        )
                    );
                    """
                )

            except Exception:

                storage = {}

            if not storage:

                continue

            for key, value in storage.items():

                key_lower = str(key).lower()

                if (
                    "token" in key_lower
                    or "auth" in key_lower
                    or "jwt" in key_lower
                    or "access" in key_lower
                ):

                    if value:

                        value_string = str(value)

                        # ------------------------------------
                        # Handle JSON token objects
                        # ------------------------------------

                        if value_string.startswith("{"):

                            try:

                                parsed = json.loads(value_string)

                                possible_tokens = [
                                    parsed.get("token"),
                                    parsed.get("accessToken"),
                                    parsed.get("access_token"),
                                    parsed.get("jwt"),
                                ]

                                for possible in possible_tokens:

                                    if possible:

                                        jwt_token = str(possible)

                                        break

                            except Exception:

                                pass

                        else:

                            jwt_token = value_string

                        if jwt_token:

                            break

            if jwt_token:

                break

        # ----------------------------------------------------
        # COOKIE FALLBACK
        # ----------------------------------------------------

        cookies = driver.get_cookies()

        if not jwt_token:

            for cookie in cookies:

                name = str(cookie.get("name", "")).lower()

                if (
                    "token" in name
                    or "auth" in name
                    or "jwt" in name
                    or "access" in name
                ):

                    jwt_token = cookie.get("value")

                    if jwt_token:

                        break

        # ----------------------------------------------------
        # TOKEN NOT FOUND
        # ----------------------------------------------------

        if not jwt_token:

            debug_html = os.path.join(OUTPUT_PATH, "login_debug.html")
            debug_png = os.path.join(OUTPUT_PATH, "login_debug.png")

            os.makedirs(OUTPUT_PATH, exist_ok=True)

            try:

                with open(debug_html, "w", encoding="utf-8") as f:

                    f.write(driver.page_source)

            except Exception:

                pass

            try:

                driver.save_screenshot(debug_png)

            except Exception:

                pass

            raise RuntimeError(
                "Authentication token was not found. "
                f"Debug files saved to: {OUTPUT_PATH}"
            )

        # ----------------------------------------------------
        # COOKIE STRING
        # ----------------------------------------------------

        cookie_string = "; ".join(
            [
                f"{cookie['name']}={cookie['value']}"
                for cookie in cookies
            ]
        )

        log("Authentication successful.", Fore.GREEN)

        return (jwt_token, cookie_string)

    except Exception:

        # ----------------------------------------------------
        # SAVE LOGIN DEBUG
        # ----------------------------------------------------

        try:

            os.makedirs(OUTPUT_PATH, exist_ok=True)

            debug_html = os.path.join(OUTPUT_PATH, "login_debug.html")
            debug_png = os.path.join(OUTPUT_PATH, "login_debug.png")

            with open(debug_html, "w", encoding="utf-8") as f:

                f.write(driver.page_source)

            try:

                driver.save_screenshot(debug_png)

            except Exception:

                pass

            log(
                (
                    "Login debug files saved: "
                    f"{debug_html} and {debug_png}"
                ),
                Fore.YELLOW
            )

        except Exception:

            pass

        raise

    finally:

        try:

            driver.quit()

        except Exception:

            pass


# ============================================================
# AUTHENTICATED SESSION
# ============================================================

class AuthSession:

    def __init__(self):

        self.jwt_token = None

        self.cookie_string = ""

        self.session = self._build_session()

        self.refresh_lock = threading.Lock()

    # --------------------------------------------------------
    # BUILD SESSION
    # --------------------------------------------------------

    def _build_session(self):

        session = requests.Session()

        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=5,
            max_retries=retry,
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    # --------------------------------------------------------
    # REFRESH AUTH
    # --------------------------------------------------------

    def refresh(self):

        with self.refresh_lock:

            log("Refreshing authentication...", Fore.YELLOW)

            jwt, cookies = do_login()

            self.jwt_token = jwt

            self.cookie_string = cookies

            self.session.headers.clear()

            self.session.headers.update(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Authorization": self.jwt_token,
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": BASE_URL,
                    "Referer": f"{BASE_URL}/",
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/153.0.0.0 "
                        "Safari/537.36"
                    ),
                }
            )

            if self.cookie_string:

                self.session.headers.update(
                    {"Cookie": self.cookie_string}
                )


# ============================================================
# GENERIC POST REQUEST
# ============================================================

def api_post(auth, url, payload):

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = auth.session.post(
                url,
                json=payload,
                timeout=30,
            )

        except requests.RequestException as e:

            if attempt >= MAX_RETRIES:

                raise RuntimeError(
                    f"Network error after "
                    f"{MAX_RETRIES} attempts: {e}"
                )

            wait_seconds = 2 ** attempt

            log(
                f"Network error: {e}. "
                f"Retrying in {wait_seconds}s...",
                Fore.YELLOW
            )

            time.sleep(wait_seconds)

            continue

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if response.status_code == 200:

            try:

                return response.json()

            except ValueError:

                raise RuntimeError(
                    "HTTP 200 received but response "
                    "was not valid JSON."
                )

        # ----------------------------------------------------
        # AUTHENTICATION
        # ----------------------------------------------------

        if response.status_code == 401:

            if attempt >= MAX_RETRIES:

                raise RuntimeError(
                    "Authentication failed repeatedly."
                )

            log(
                "HTTP 401 — refreshing authentication...",
                Fore.YELLOW
            )

            time.sleep(3)

            auth.refresh()

            continue

        # ----------------------------------------------------
        # FORBIDDEN
        # ----------------------------------------------------

        if response.status_code == 403:

            raise RuntimeError(
                "HTTP 403 Forbidden. "
                "The authenticated account does not have "
                "permission for this request."
            )

        # ----------------------------------------------------
        # RATE LIMIT
        # ----------------------------------------------------

        if response.status_code == 429:

            retry_after = response.headers.get("Retry-After")

            try:

                wait_seconds = int(retry_after)

            except (TypeError, ValueError):

                wait_seconds = DEFAULT_RATE_LIMIT_WAIT

            wait_seconds = min(max(wait_seconds, 5), 300)

            if attempt >= MAX_RETRIES:

                raise RuntimeError(
                    "HTTP 429 persisted after retries."
                )

            log(
                f"HTTP 429 — waiting {wait_seconds}s...",
                Fore.YELLOW
            )

            time.sleep(wait_seconds)

            continue

        # ----------------------------------------------------
        # SERVER ERROR
        # ----------------------------------------------------

        if response.status_code >= 500:

            if attempt >= MAX_RETRIES:

                raise RuntimeError(
                    f"Server error "
                    f"{response.status_code}: "
                    f"{response.text[:500]}"
                )

            wait_seconds = 2 ** attempt

            log(
                f"HTTP {response.status_code} — "
                f"retrying in {wait_seconds}s...",
                Fore.YELLOW
            )

            time.sleep(wait_seconds)

            continue

        # ----------------------------------------------------
        # OTHER ERROR
        # ----------------------------------------------------

        raise RuntimeError(
            f"Unexpected HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    raise RuntimeError("API request failed.")


# ============================================================
# STALE / COUNT STATE
# ============================================================

def load_signup_state():

    if not os.path.exists(STATE_FILE):

        return {}

    try:

        with open(STATE_FILE, "r", encoding="utf-8") as f:

            data = json.load(f)

        if isinstance(data, dict):

            return data

    except (OSError, json.JSONDecodeError) as e:

        log(f"Could not read signup state: {e}", Fore.YELLOW)

    return {}


def save_signup_state(state):

    os.makedirs(OUTPUT_PATH, exist_ok=True)

    temp_file = STATE_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:

        json.dump(state, f, indent=2)

    os.replace(temp_file, STATE_FILE)


def get_affiliate_key(affiliate):

    return str(affiliate["accountId"])


def split_stale_affiliates(affiliates, previous_state):

    stale = []

    unchanged = []

    for affiliate in affiliates:

        key = get_affiliate_key(affiliate)

        current_count = int(
            affiliate.get("lifeTimeSignUps", 0) or 0
        )

        previous = previous_state.get(key)

        # ----------------------------------------------------
        # NEW AFFILIATE
        # ----------------------------------------------------

        if previous is None:

            stale.append(affiliate)

            log(
                (
                    f"{affiliate['username']} → "
                    f"NEW · signups={current_count} · "
                    f"PROCESS"
                ),
                Fore.YELLOW
            )

            continue

        # ----------------------------------------------------
        # PREVIOUS COUNT
        # ----------------------------------------------------

        try:

            previous_count = int(
                previous.get("signup_count", 0) or 0
            )

        except (TypeError, ValueError):

            previous_count = 0

        # ----------------------------------------------------
        # COUNT CHANGED
        # ----------------------------------------------------

        if current_count != previous_count:

            stale.append(affiliate)

            log(
                (
                    f"{affiliate['username']} → "
                    f"COUNT CHANGED "
                    f"{previous_count} → "
                    f"{current_count} · "
                    f"PROCESS"
                ),
                Fore.YELLOW
            )

        # ----------------------------------------------------
        # COUNT UNCHANGED
        # ----------------------------------------------------

        else:

            unchanged.append(affiliate)

            log(
                (
                    f"{affiliate['username']} → "
                    f"unchanged ({current_count}) · "
                    f"SKIP"
                ),
                Style.DIM
            )

    return (stale, unchanged)


def update_successful_counts(state, processed_affiliates):

    for affiliate in processed_affiliates:

        key = get_affiliate_key(affiliate)

        state[key] = {

            "signup_count": int(
                affiliate.get("lifeTimeSignUps", 0) or 0
            ),

            "username": affiliate.get("username", ""),

            "updated_at": datetime.now(INDIA_TZ).isoformat(),
        }


# ============================================================
# STEP 1
# DISCOVER SUB-AFFILIATES
# ============================================================

def fetch_sub_affiliates(auth):

    log_banner("DISCOVERING SUB-AFFILIATES")

    payload = {
        "page_size": DISCOVERY_PAGE_SIZE,
        "page_token": 0,
        "parent_id": MASTER_AFFILIATE_ID,
        "role": "Master-Affiliate",
    }

    all_affiliates = []

    while True:

        data = api_post(auth, AFFILIATE_ACCOUNTS_URL, payload)

        affiliates = data.get("affiliateDetailsList", [])

        if not isinstance(affiliates, list):

            raise RuntimeError(
                "Unexpected affiliateDetailsList format."
            )

        all_affiliates.extend(affiliates)

        next_token = data.get("nextPageToken")

        if not next_token:

            break

        payload["page_token"] = next_token

        random_pause(*DISCOVERY_DELAY)

    # --------------------------------------------------------
    # ONLY SUB-AFFILIATES
    # --------------------------------------------------------

    sub_affiliates = []

    for affiliate in all_affiliates:

        if not isinstance(affiliate, dict):

            continue

        role = affiliate.get("role")

        account_id = affiliate.get("accountId")

        username = affiliate.get("userName")

        if role == "Sub-Affiliate" and account_id:

            try:

                account_id = int(account_id)

            except (TypeError, ValueError):

                continue

            sub_affiliates.append(
                {
                    "accountId": account_id,

                    "username": username or "",

                    "parentId": affiliate.get("parentId"),

                    "lifeTimeFTDAmount": affiliate.get(
                        "lifeTimeFTDAmount", 0
                    ),

                    "lifeTimeFirstDeposits": affiliate.get(
                        "lifeTimeFirstDeposits", 0
                    ),

                    "lifeTimeSignUps": affiliate.get(
                        "lifeTimeSignUps", 0
                    ),

                    "affiliatePath": affiliate.get(
                        "affiliatePath", ""
                    ),
                }
            )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    log(f"Master affiliate: {MASTER_AFFILIATE_ID}", Fore.CYAN)

    log(
        f"Sub-affiliates discovered: {len(sub_affiliates)}",
        Fore.GREEN
    )

    for affiliate in sub_affiliates:

        log(
            (
                f"{affiliate['username']} "
                f"→ parentId={affiliate['accountId']} "
                f"→ signups={affiliate['lifeTimeSignUps']} "
                f"→ FTD={affiliate['lifeTimeFirstDeposits']} "
                f"→ FTD amount={affiliate['lifeTimeFTDAmount']}"
            ),
            Style.DIM
        )

    return sub_affiliates


# ============================================================
# STEP 2
# FETCH USERS UNDER ONE SUB-AFFILIATE
# ============================================================

def fetch_users_for_affiliate(auth, affiliate):

    parent_id = affiliate["accountId"]

    affiliate_name = affiliate["username"]

    log(
        f"Fetching users for {affiliate_name} [parentId={parent_id}]",
        Fore.CYAN
    )

    payload = {
        "user": "",
        "parentId": parent_id,
        "sortOrder": "",
        "pageSize": PAGE_SIZE,
    }

    all_users = []

    page = 1

    while True:

        if page > 1:

            random_pause(*DELAY_API_CALLS)

        data = api_post(auth, REPORT_URL, payload)

        users = data.get("userDetailsList", [])

        if not isinstance(users, list):

            raise RuntimeError(
                "Unexpected userDetailsList format."
            )

        # ----------------------------------------------------
        # ATTACH AFFILIATE INFORMATION
        # ----------------------------------------------------

        for user in users:

            if not isinstance(user, dict):

                continue

            user["affiliate_parent_id"] = parent_id

            user["Affiliate Name"] = affiliate_name

        all_users.extend(users)

        log(
            (
                f"{affiliate_name} · "
                f"page {page:03d} · "
                f"{len(users)} records · "
                f"total {len(all_users)}"
            ),
            Style.DIM
        )

        # ----------------------------------------------------
        # PAGINATION
        # ----------------------------------------------------

        next_token = data.get("nextPageToken")

        if not next_token:

            break

        payload["pageToken"] = next_token

        page += 1

    log(
        f"{affiliate_name} complete — {len(all_users)} users",
        Fore.GREEN
    )

    return all_users


# ============================================================
# STEP 3
# FETCH ALL SELECTED AFFILIATES
# ============================================================

def fetch_all_users(auth, affiliates):

    all_records = []

    for index, affiliate in enumerate(affiliates):

        records = fetch_users_for_affiliate(auth, affiliate)

        all_records.extend(records)

        if index < len(affiliates) - 1:

            delay = random.uniform(*DELAY_AFFILIATE_SWITCH)

            log(
                f"Waiting {delay:.1f}s before next affiliate...",
                Style.DIM
            )

            time.sleep(delay)

    return all_records


# ============================================================
# PROCESS DATA
# ============================================================

def process(records):

    df = pd.DataFrame(records)

    if df.empty:

        return df

    # ========================================================
    # NUMERIC COLUMNS
    # ========================================================

    aggregate_columns = [
        "availableBalance",
        "myPLPoints",
        "exposure",
        "lifeTimeProfit",
    ]

    for column in aggregate_columns:

        if column not in df.columns:

            df[column] = 0

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

    # ========================================================
    # AGGREGATE
    # ========================================================

    df["Aggregate"] = df[aggregate_columns].sum(axis=1)

    # ========================================================
    # ONLY ZERO AGGREGATE
    # ========================================================

    df = df[df["Aggregate"] == 0].copy()

    log(f"Rows after aggregate filter: {len(df)}", Fore.CYAN)

    if df.empty:

        return df

    # ========================================================
    # FIXED OUTPUT FIELDS
    # ========================================================

    df["language"] = "Hindi"

    df["Website Name"] = "wfix.fun"

    df["Account Id"] = df["username"]

    # ========================================================
    # LEAD SOURCE 2  →  <affiliate name>_Auto
    # e.g. winfix_tg1234 → winfix_tg1234_Auto
    # ========================================================

    df["Lead Source 2"] = (
        df["Affiliate Name"]
        .fillna("")
        .astype(str)
        .str.strip()
        + LEAD_SOURCE_SUFFIX
    )

    # ========================================================
    # CREATE TIME
    # ========================================================

    if "createTime" not in df.columns:

        raise RuntimeError(
            "createTime column missing from API response."
        )

    df["createTime"] = pd.to_datetime(
        df["createTime"],
        utc=True,
        errors="coerce"
    )

    df = df.dropna(subset=["createTime"]).copy()

    if df.empty:

        return df

    # ========================================================
    # UTC → INDIA
    # ========================================================

    df["createTime"] = df["createTime"].dt.tz_convert(INDIA_TZ)

    # ========================================================
    # YESTERDAY + TODAY (disabled)
    # ========================================================

    today_ist = pd.Timestamp.now(tz=INDIA_TZ).normalize()
    start_date_ist = today_ist - pd.Timedelta(days=1)
    end_date_ist = today_ist + pd.Timedelta(days=1)
    
    df = df[
        (df["createTime"] >= start_date_ist)
        & (df["createTime"] < end_date_ist)
    ].copy()
    
    log(f"Rows after yesterday + today filter: {len(df)}", Fore.CYAN)
    
    if df.empty:
        return df

    # ========================================================
    # FORMAT CREATED TIME
    # ========================================================

    df["createTime"] = df["createTime"].dt.strftime("%d/%m/%Y %H:%M")

    # ========================================================
    # RENAME
    # ========================================================

    df = df.rename(
        columns={
            "createTime": "Created Time",
            "username": "Username",
        }
    )

    # ========================================================
    # REQUIRED OUTPUT
    # ========================================================

    required_columns = [
        "phoneNumber",
        "Username",
        "Lead Source 2",
        "language",
        "Website Name",
        "Account Id",
        "Created Time",
    ]

    for column in required_columns:

        if column not in df.columns:

            df[column] = ""

    df = df[required_columns].copy()

    # ========================================================
    # PHONE CLEANUP
    # ========================================================

    df = df[df["phoneNumber"].notna()].copy()

    df["phoneNumber"] = (
        df["phoneNumber"]
        .astype(str)
        .str.strip()
    )

    df = df[
        ~df["phoneNumber"].isin(["", "nan", "None", "null"])
    ].copy()

    return df


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(df):

    os.makedirs(OUTPUT_PATH, exist_ok=True)

    output_file = os.path.join(OUTPUT_PATH, OUTPUT_FILENAME)

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    log(f"CSV saved: {output_file}", Fore.GREEN)

    return output_file


# ============================================================
# DONE FILE
# ============================================================

def write_done_file():

    os.makedirs(OUTPUT_PATH, exist_ok=True)

    done_file = os.path.join(OUTPUT_PATH, "scraper_done.txt")

    with open(done_file, "w", encoding="utf-8") as f:

        f.write("done")

    log(f"Done file created: {done_file}", Fore.GREEN)


# ============================================================
# MAIN
# ============================================================

def main():

    log_banner("VIKRANT AFFILIATE EXTRACTION")

    start_time = time.time()

    validate_config()

    log(f"Master affiliate: {MASTER_AFFILIATE_ID}", Fore.CYAN)

    # ========================================================
    # AUTHENTICATE
    # ========================================================

    auth = AuthSession()

    auth.refresh()

    # ========================================================
    # DISCOVER SUB-AFFILIATES
    # ========================================================

    affiliates = fetch_sub_affiliates(auth)

    if not affiliates:

        log("No sub-affiliates were returned.", Fore.YELLOW)

        return

    # ========================================================
    # LOAD PREVIOUS COUNTS
    # ========================================================

    previous_state = load_signup_state()

    log(
        f"Previously tracked affiliates: {len(previous_state)}",
        Fore.CYAN
    )

    # ========================================================
    # COMPARE CURRENT COUNTS
    # ========================================================

    stale_affiliates, unchanged_affiliates = split_stale_affiliates(
        affiliates,
        previous_state
    )

    log(
        (
            f"Affiliate comparison: "
            f"{len(stale_affiliates)} need processing, "
            f"{len(unchanged_affiliates)} unchanged"
        ),
        Fore.CYAN
    )

    # ========================================================
    # NO CHANGES
    # ========================================================

    if not stale_affiliates:

        log(
            (
                "No affiliate signup counts changed. "
                "Skipping user-data fetch."
            ),
            Fore.GREEN
        )

        write_done_file()

        elapsed = time.time() - start_time

        log_banner(
            f"COMPLETE · 0 new/changed affiliates · {elapsed:.1f}s"
        )

        return

    # ========================================================
    # FETCH ONLY CHANGED / NEW AFFILIATES
    # ========================================================

    log_banner("FETCHING CHANGED AFFILIATES")

    records = fetch_all_users(auth, stale_affiliates)

    # ========================================================
    # UPDATE STATE ONLY AFTER FETCH SUCCEEDS
    # ========================================================
    #
    # If fetching an affiliate fails, the script raises an
    # exception before this point, so its new count is NOT
    # saved as processed.
    #
    # ========================================================

    update_successful_counts(previous_state, stale_affiliates)

    save_signup_state(previous_state)

    log(
        f"Signup state updated for {len(stale_affiliates)} affiliates.",
        Fore.GREEN
    )

    # ========================================================
    # NO USER RECORDS
    # ========================================================

    if not records:

        log(
            "No users were returned for changed affiliates.",
            Fore.YELLOW
        )

        write_done_file()

        return

    log(f"Raw user records fetched: {len(records)}", Fore.CYAN)

    # ========================================================
    # PROCESS
    # ========================================================

    df = process(records)

    if df.empty:

        log("No leads remained after processing.", Fore.YELLOW)

        write_done_file()

        return

    # ========================================================
    # SAVE
    # ========================================================

    save_csv(df)

    write_done_file()

    # ========================================================
    # SUMMARY
    # ========================================================

    elapsed = time.time() - start_time

    log_banner(
        (
            f"COMPLETE · "
            f"{len(df)} records · "
            f"{len(stale_affiliates)} affiliates processed · "
            f"{len(unchanged_affiliates)} skipped · "
            f"{elapsed:.1f}s"
        )
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        log("Stopped by user.", Fore.YELLOW)

    except Exception as e:

        log(f"Fatal error: {e}", Fore.RED)

        raise