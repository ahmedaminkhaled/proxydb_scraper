import time
import threading
from queue import Queue
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Settings
TOTAL_PROXIES = 14140
PROXIES_PER_PAGE = 30
THREAD_COUNT = 5

# Global results
proxy_list = []
lock = threading.Lock()


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=chrome_options)


def scrape_page(offset):
    url = f"https://proxydb.net/?offset={offset}"
    driver = create_driver()

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
        )
        time.sleep(1.5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find("table", class_="table")

        if not table:
            print(f"[{offset}] No table found.")
            return

        for row in table.select("tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                ip = cols[0].get_text(strip=True)
                port = cols[1].get_text(strip=True)
                proxy = f"{ip}:{port}"

                with lock:
                    proxy_list.append(proxy)

        print(f"[{offset}] Scraped page with {len(table.select('tbody tr'))} proxies.")
    except Exception as e:
        print(f"[{offset}] Error: {e}")
    finally:
        driver.quit()


def worker(queue):
    while not queue.empty():
        offset = queue.get()
        scrape_page(offset)
        queue.task_done()


def main():
    print("Starting ProxyDB scraper...")

    job_queue = Queue()
    for offset in range(0, TOTAL_PROXIES, PROXIES_PER_PAGE):
        job_queue.put(offset)

    threads = []
    for _ in range(THREAD_COUNT):
        t = threading.Thread(target=worker, args=(job_queue,))
        t.start()
        threads.append(t)

    job_queue.join()

    with open("proxydb_proxies_all.txt", "w") as f:
        for proxy in proxy_list:
            f.write(proxy + "\n")

    print(f"Finished scraping {len(proxy_list)} proxies.")
    print("Saved to: proxydb_proxies_all.txt")


if __name__ == "__main__":
    main()
