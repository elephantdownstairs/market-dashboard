from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

@app.route('/analyze', methods=['POST'])
def analyze_market():
    """
    Analyze market movements using free web scraping
    Expects JSON: {
        "symbols": [
            {"symbol": "^GSPC", "name": "S&P 500", "changePercent": 2.5},
            ...
        ],
        "startDate": "2024-01-01",
        "endDate": "2024-01-08"
    }
    """
    try:
        data = request.json
        symbols = data.get('symbols', [])
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        
        if not symbols:
            return jsonify({"error": "No symbols provided"}), 400
        
        analyses = []
        
        for symbol_data in symbols:
            symbol = symbol_data['symbol']
            name = symbol_data['name']
            change_percent = symbol_data['changePercent']
            
            # Get free news analysis
            analysis = get_free_news_analysis(symbol, name, change_percent, start_date, end_date)
            
            analyses.append({
                "symbol": symbol,
                "name": name,
                "changePercent": change_percent,
                "analysis": analysis
            })
            
            # Rate limiting to be nice to free services
            time.sleep(1)
        
        return jsonify({"analyses": analyses})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_free_news_analysis(symbol, name, change_percent, start_date, end_date):
    """
    Scrape free news sources for market analysis
    Uses: Google News, Yahoo Finance News, and general web search
    """
    try:
        drivers = []
        sources = []
        
        # Method 1: Yahoo Finance News (built into Yahoo Finance)
        yahoo_news = scrape_yahoo_finance_news(symbol, name)
        if yahoo_news:
            drivers.extend(yahoo_news['drivers'])
            sources.extend(yahoo_news['sources'])
        
        # Method 2: Google News search
        google_news = scrape_google_news(name, change_percent)
        if google_news:
            drivers.extend(google_news['drivers'])
            sources.extend(google_news['sources'])
        
        # Method 3: Finviz news (free financial news aggregator)
        finviz_news = scrape_finviz_news(symbol, name)
        if finviz_news:
            drivers.extend(finviz_news['drivers'])
            sources.extend(finviz_news['sources'])
        
        # Deduplicate and limit
        drivers = list(dict.fromkeys(drivers))[:3]  # Top 3 unique drivers
        sources = list(dict.fromkeys(sources))[:5]  # Top 5 unique sources
        
        # If no drivers found, provide generic analysis
        if not drivers:
            direction = "increased" if change_percent > 0 else "decreased"
            drivers = [
                f"{name} {direction} by {abs(change_percent):.2f}% during this period.",
                "Check financial news sources for detailed analysis of market conditions.",
                "Consider broader market trends and sector-specific factors."
            ]
            sources = [
                f"Yahoo Finance - https://finance.yahoo.com/quote/{symbol}",
                f"Google Finance - https://www.google.com/finance/quote/{symbol.replace('^', '')}:INDEXSP"
            ]
        
        return {
            "drivers": drivers,
            "sources": sources,
            "method": "free_scraping"
        }
    
    except Exception as e:
        return {
            "drivers": [f"Unable to fetch news: {str(e)}"],
            "sources": [],
            "method": "error"
        }

def scrape_yahoo_finance_news(symbol, name):
    """Scrape Yahoo Finance news tab"""
    try:
        # Yahoo Finance news URL
        url = f"https://finance.yahoo.com/quote/{symbol}/news"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        drivers = []
        sources = []
        
        # Find news articles
        articles = soup.find_all('h3', class_='Mb(5px)')[:3]  # Top 3 articles
        
        for article in articles:
            title = article.get_text().strip()
            link_elem = article.find_parent('a')
            link = f"https://finance.yahoo.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else ""
            
            if title:
                drivers.append(title)
                if link:
                    sources.append(f"{title[:50]}... - {link}")
        
        return {'drivers': drivers, 'sources': sources} if drivers else None
    
    except Exception as e:
        print(f"Yahoo Finance scraping error: {e}")
        return None

def scrape_google_news(name, change_percent):
    """Search Google News for market analysis"""
    try:
        # Google News search URL
        query = f"{name} stock market news"
        url = f"https://news.google.com/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        drivers = []
        sources = []
        
        # Find news articles
        articles = soup.find_all('article')[:3]
        
        for article in articles:
            title_elem = article.find('a', class_='JtKRv')
            if title_elem:
                title = title_elem.get_text().strip()
                # Google News uses relative URLs
                link = f"https://news.google.com{title_elem['href'][1:]}" if 'href' in title_elem.attrs else ""
                
                if title:
                    drivers.append(title)
                    if link:
                        sources.append(f"{title[:50]}... - {link}")
        
        return {'drivers': drivers, 'sources': sources} if drivers else None
    
    except Exception as e:
        print(f"Google News scraping error: {e}")
        return None

def scrape_finviz_news(symbol, name):
    """Scrape Finviz for financial news"""
    try:
        # Convert symbol to ticker format (remove ^ and special chars)
        ticker = symbol.replace('^', '').replace('=X', '').replace('=F', '')
        
        # Finviz URL
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        drivers = []
        sources = []
        
        # Find news table
        news_table = soup.find('table', class_='fullview-news-outer')
        if news_table:
            news_items = news_table.find_all('tr')[:3]
            
            for item in news_items:
                link_elem = item.find('a')
                if link_elem:
                    title = link_elem.get_text().strip()
                    link = link_elem['href'] if 'href' in link_elem.attrs else ""
                    
                    if title:
                        drivers.append(title)
                        if link:
                            sources.append(f"{title[:50]}... - {link}")
        
        return {'drivers': drivers, 'sources': sources} if drivers else None
    
    except Exception as e:
        print(f"Finviz scraping error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "method": "free_scraping",
        "sources": ["Yahoo Finance", "Google News", "Finviz"],
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print("📊 Market Analysis Backend Ready (100% FREE)")
    print("📰 News Sources: Yahoo Finance, Google News, Finviz")
    print("🔗 Server running on http://localhost:5000")
    print("💰 Cost: $0 - Completely free!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
