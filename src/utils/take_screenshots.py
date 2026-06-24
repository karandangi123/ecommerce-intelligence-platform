from playwright.sync_api import sync_playwright

def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1400})
        page.goto('http://localhost:8000')
        
        # Wait for initial charts to render
        page.wait_for_timeout(3000)
        
        # CEO Tab (already saved as dashboard_preview.png, but let's re-save to be safe)
        page.screenshot(path='assets/dashboard_ceo.png', full_page=True)
        print("CEO screenshot saved.")
        
        # Ops Tab
        page.evaluate("switchTab('ops')")
        page.wait_for_timeout(1000)
        page.screenshot(path='assets/dashboard_ops.png', full_page=True)
        print("Ops screenshot saved.")
        
        # Marketing Tab
        page.evaluate("switchTab('marketing')")
        page.wait_for_timeout(1000)
        page.screenshot(path='assets/dashboard_mkt.png', full_page=True)
        print("Marketing screenshot saved.")
        
        browser.close()

if __name__ == "__main__":
    take_screenshots()
