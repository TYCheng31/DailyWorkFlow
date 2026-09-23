import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import time
import re
import requests 
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

class DiscordLogger:
    def __init__(self):
        self.token = os.getenv("DISCORD_TOKEN")
        self.channel_id = os.getenv("CHANNEL_ID")
        self.api_url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

    def send_message(self, message, parse_mode=None):
        """傳送訊息到 Discord (Discord 預設支援 Markdown，不需特別指定 parse_mode)"""
        if not self.token or not self.channel_id:
            print("Discord Token 或 Channel ID 未設定！")
            return
            
        payload = {"content": message}
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status() 
        except Exception as e:
            print(f"Discord 訊息發送失敗: {e}")

d_logger = DiscordLogger()
log_buffer = []

def log_print(message):
    """Print to console and append to log buffer."""
    print(message)
    log_buffer.append(str(message))

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('banklinker-473405-6be3b03228c7.json', scope)
client = gspread.authorize(creds)
sheet = client.open("Bank").worksheet("總明細")

HEADLESS = True

chrome_options = Options()
if HEADLESS:
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
else:
    chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=chrome_options)

class Bank:
    def __init__(self):
        self.login_id = 0
        self.login_account = 0
        self.login_password = 0
        self.main_account = ""
        self.cash = 0
        self.exchange = 0
        self.stock = 0

Esun = Bank()
Esun.login_id = os.getenv("ESUN_ID")
Esun.login_account = os.getenv("ESUN_ACCOUNT")
Esun.login_password = os.getenv("ESUN_PASSWORD")

Cathay = Bank()
Cathay.login_id = os.getenv("CATHAY_ID")
Cathay.login_account = os.getenv("CATHAY_ACCOUNT")
Cathay.login_password = os.getenv("CATHAY_PASSWORD")

Line = Bank()
Line.login_id = os.getenv("LINE_ID")
Line.login_account = os.getenv("LINE_ACCOUNT")
Line.login_password = os.getenv("LINE_PASSWORD")

wait = WebDriverWait(driver, 60)

def EsunSpider():
    try:
        driver.get("https://ebank.esunbank.com.tw/index.jsp")
        wait = WebDriverWait(driver, 20)

        # 1. 強制輸入身分證字號/統一編號
        id_input = wait.until(
            EC.presence_of_element_located((By.NAME, "id"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", id_input, Esun.login_id)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", id_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", id_input)

        # 2. 強制輸入使用者名稱
        user_input = wait.until(
            EC.presence_of_element_located((By.NAME, "userName"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", user_input, Esun.login_account)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", user_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", user_input)

        # 3. 強制輸入使用者密碼
        pwd_input = wait.until(
            EC.presence_of_element_located((By.NAME, "pxssword"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", pwd_input, Esun.login_password)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pwd_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", pwd_input)

        # 4. 強制點擊登入按鈕
        login_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn-main-fill') and span[text()='登入']]"))
        ) 
        # 使用 JavaScript 強制點擊 (無視遮罩與畫面位置)
        driver.execute_script("arguments[0].click();", login_btn)

        # ================= 處理可能出現的「確定登入」按鈕 =================
        try:
            # 設定較短的等待時間 (3秒)，避免沒出現時腳本卡住太久
            short_wait = WebDriverWait(driver, 3)
            confirm_login_btn = short_wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'modal-default-button') and span[text()='確定登入']]"))
            )
            driver.execute_script("arguments[0].click();", confirm_login_btn)
        except TimeoutException:
            # 如果 3 秒內沒找到該按鈕，代表正常登入，直接 pass 繼續執行下一步
            pass
        except Exception as e:
        # =====================================================================

        # 登入後畫面切換需要時間渲染前端框架，強制等待 4 秒
        time.sleep(4)

        # 5. 點擊「資產負債表」頁籤
        # 改用 element_to_be_clickable，確保按鈕處於可被互動的狀態
        balance_sheet_tab = wait.until(
            EC.element_to_be_clickable((By.ID, "CCOA1002"))
        )
        try:
            # 使用 ActionChains 模擬真實使用者的「滑鼠移至元素上 -> 點擊」
            ActionChains(driver).move_to_element(balance_sheet_tab).click().perform()
        except Exception as click_err:
            driver.execute_script("arguments[0].click();", balance_sheet_tab)

        # 點擊完之後，再稍微等個 2 秒，讓底下的金額數字讀取出來
        time.sleep(2)

        # 6. 取得「臺幣存款」的金額
        cash_element = wait.until(
            EC.presence_of_element_located((
                By.XPATH, 
                "//div[text()='臺幣存款']/ancestor::div[contains(@class, 'main-content-wrapper')]//div[contains(@class, 'legend-item-value')]//span"
            ))
        )
        # 取得文字，使用 textContent 確保不受前端畫面遮罩影響
        cash_text = cash_element.get_attribute("textContent").strip().replace(",", "")
        # 轉換成整數並存入原本的變數中
        Esun.cash = int(cash_text)
        print(f"ESUNcash: {Esun.cash}")

        # 7. 取得「投資 / 證券」的金額
        stock_element = wait.until(
            EC.presence_of_element_located((
                By.XPATH, 
                "//div[text()='投資 / 證券']/ancestor::div[contains(@class, 'main-content-wrapper')]//div[contains(@class, 'legend-item-value')]//span"
            ))
        )
        # 取得文字，清除逗號並轉為整數
        stock_text = stock_element.get_attribute("textContent").strip().replace(",", "")
        # 存入原本的 stock 變數中
        Esun.stock = int(stock_text)
        print(f"ESUNstock: {Esun.stock}")

        # 8. 強制點擊登出圖示
        logout_icon = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".header-option-entry-logout-icon"))
        )
        # 使用 JavaScript 強制點擊
        driver.execute_script("arguments[0].click();", logout_icon)

    except Exception as e:
        # 如果你有自定義的 log_print 請確保有該函式，或者直接用 print
        print(f"Error in EsunSpider: {e}")
    
def CathaySpider():
    try:
        driver.get("https://www.cathaybk.com.tw/mybank/")

        cust_input = wait.until(
            EC.visibility_of_element_located((By.ID, "CustID"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", cust_input, Cathay.login_id)

        cust_input = wait.until(
            EC.visibility_of_element_located((By.ID, "UserIdKeyin"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", cust_input, Cathay.login_account)

        cust_input = wait.until(
            EC.visibility_of_element_located((By.ID, "PasswordKeyin"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", cust_input, Cathay.login_password)

        loginButton = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @class='btn no-print btn-fill js-login btn btn-fill w-100 u-pos-relative' and @onclick='NormalDataCheck()']"))
        )
        driver.execute_script("arguments[0].click();", loginButton)
        time.sleep(10)

        ###TWD
        button_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[data-evt="home_twd_overview"]'))
        )
        raw_text = button_element.text
        clean_text = raw_text.replace("TWD", "").replace(",", "").strip()
        Cathay.cash = int(clean_text)
        print(f"CATHAY_TWD: {Cathay.cash}")

        ###Foreign
        foreign_currency_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[data-evt="home_foreign_currency_overview"]'))
        )
        foreign_currency_text = foreign_currency_element.text
        clean_text = foreign_currency_text.replace("TWD", "").replace(",", "").strip().split()[0]
        Cathay.exchange = int(clean_text)
        print(f"CATHAYForeign: {Cathay.exchange}")

        ###STOCK
        xpath_selector = "//p[text()='投資']/parent::div/following-sibling::div[@class='css-iu1euh']/p"
        
        investment_element = wait.until(
            EC.visibility_of_element_located((By.XPATH, xpath_selector))
        )
        
        investment_text = investment_element.text
        clean_text = investment_text.replace("TWD", "").replace(",", "").strip().split()[0]
        Cathay.stock = int(clean_text)
        print(f"CATHAYstock: {Cathay.stock}")

        ###LOGOUT
        logout_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-evt="onlinebanking-logout"]'))
        )
        driver.execute_script("arguments[0].click();", logout_button)
    except Exception as e:
        log_print(f"Error in CathaySpider: {e}")


def LineSpider():
    try:
        driver.get("https://accessibility.linebank.com.tw/transaction")

        wait.until(EC.presence_of_element_located((By.ID, "nationalId"))).send_keys(Line.login_id)
        wait.until(EC.presence_of_element_located((By.ID, "userId"))).send_keys(Line.login_account)
        wait.until(EC.presence_of_element_located((By.ID, "pw"))).send_keys(Line.login_password)

        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@title='登入友善網路銀行']"))
        )
        login_btn.click()

        confirm_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@title='確定']"))
        )
        confirm_btn.click()

        dropdown_element = wait.until(
            EC.presence_of_element_located((By.ID, "account-dropdown"))
        )
        select = Select(dropdown_element)
        select.select_by_value("111003906466")


        p_element = wait.until(
            EC.presence_of_element_located((By.XPATH, "//p[contains(., '可用餘額')]"))
        )
        
        raw_text = p_element.text
        
        m = re.search(r"可用餘額\s*:\s*NT\$([0-9,]+)", raw_text)
        if m:
            Line.cash = int(m.group(1).replace(",", ""))
            print(f"LINEcash: {Line.cash}")
        else:
            print("警告：抓到了標籤，但格式無法解析！")
        
    except Exception as e:
        log_print(f"Error in LineSpider: {e}")
    
def JudgeColor(SheetRow, row):
    if SheetRow < 0:
        sheet.format(row, {'backgroundColor': {'red': 1, 'green': 0, 'blue': 0}})
    elif SheetRow > 0:
        sheet.format(row, {'backgroundColor': {'red': 0, 'green': 1, 'blue': 0}})
    elif SheetRow == 0:
        sheet.format(row, {'backgroundColor': {'red': 1, 'green': 1, 'blue': 1}})


try:
    log_print("Starting AutoAccount Task...")
    EsunSpider()
    CathaySpider()
    LineSpider()

    total_cash = Esun.cash + Cathay.cash + Line.cash
    total_exchange = Cathay.exchange
    total_stock = Esun.stock + Cathay.stock
    total_assets = total_cash + total_exchange + total_stock
    
    log_print(f"Total Cash: {total_cash}")
    log_print(f"Total Exchange: {total_exchange}")
    log_print(f"Total Stock: {total_stock}")
    log_print(f"Total Assets: {total_assets}")

    C3_value = int(sheet.cell(3, 3).value)
    D3_value = int(sheet.cell(3, 4).value) 
    E3_value = int(sheet.cell(3, 5).value) 
    F3_value = int(sheet.cell(3, 6).value) 

    cash_diff = total_cash - C3_value
    exchange_diff = total_exchange - D3_value
    stock_diff = total_stock - E3_value
    assets_diff = total_assets - F3_value

    current_date = (datetime.now() + timedelta(days=1)).strftime("%Y/%m/%d")    
    current_time = (datetime.now() + timedelta(hours=8)).strftime("%H:%M:%S")

    sheet.insert_row([current_date, current_time, 
                    total_cash, total_exchange, total_stock, total_assets, 
                    cash_diff, exchange_diff, stock_diff, assets_diff, " ", 
                    Esun.main_account, Esun.cash, Esun.exchange, Esun.stock, " ",  
                    Cathay.main_account, Cathay.cash, Cathay.exchange, Cathay.stock, " ",  
                    Line.main_account, Line.cash, Line.exchange, Line.stock
                    ], 3)

    G3_value = int(sheet.cell(3, 7).value)   
    H3_value = int(sheet.cell(3, 8).value)
    I3_value = int(sheet.cell(3, 9).value)
    J3_value = int(sheet.cell(3, 10).value)

    JudgeColor(G3_value, 'G3')
    JudgeColor(H3_value, 'H3')
    JudgeColor(I3_value, 'I3')
    JudgeColor(J3_value, 'J3')
    
    log_print("Task Completed Successfully.")
    
    def fmt(label, value=None, suffix=''):
        if value is None:
            return label
        if suffix == '%':
            return f"{label:<15}: {value:>13.2%}"
        return f"{label:<15}: {value:>13,}"

    summary_message = (
        f"```\n"
        f"AutoAccount Report \n"
        f"{current_date} {current_time}\n\n"
        f"{fmt('CASH RATIO', (total_cash + total_exchange )/total_assets,'%')}\n"
        f"-------------------------------\n" 
        f"{fmt('CHANGE')}\n"
        f"{fmt('Cash', cash_diff)}\n"
        f"{fmt('Exchange', exchange_diff)}\n"
        f"{fmt('Stock', stock_diff)}\n"
        f"{fmt('Assets', assets_diff)}\n"
        f"-------------------------------\n" 
        f"{fmt('SUM')}\n"
        f"{fmt('Cash', total_cash)}\n"
        f"{fmt('Exchange', total_exchange)}\n"
        f"{fmt('Stock', total_stock)}\n"
        f"{fmt('Assets', total_assets)}\n"
        f"-------------------------------\n"
        f"```" 
    )

    d_logger.send_message(summary_message)


except Exception as e:
    error_msg = f"Execution Failed: {e}"
    log_print(error_msg)
    d_logger.send_message(error_msg)
finally:
    try:
        driver.quit()
    except:
        pass
