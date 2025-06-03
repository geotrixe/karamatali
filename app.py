from flask import Flask, render_template, request, jsonify, send_file
from flask_wtf.csrf import CSRFProtect, generate_csrf
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import json
from urllib.parse import urlparse, quote, urljoin, unquote
import io
import time
import base64
from PIL import Image, ImageEnhance

# Initialize thread_local storage
thread_local = threading.local()

# Load environment variables
load_dotenv()

# Debug print for API key
api_key = os.getenv('GOOGLE_PLACES_API_KEY')
if api_key:
    print(f"API Key loaded (first 10 chars): {api_key[:10]}...")
else:
    print("Warning: No API key found in .env file")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
csrf = CSRFProtect(app)

# Configure requests session with retries and timeouts
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

def get_driver():
    """Initialize and return a Chrome WebDriver instance."""
    try:
        if not hasattr(thread_local, "driver"):
            print("Initializing Chrome WebDriver...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(30)
                thread_local.driver = driver
                print("Chrome WebDriver initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Chrome WebDriver: {str(e)}")
                raise
        return thread_local.driver
    except Exception as e:
        print(f"Error in get_driver: {str(e)}")
        raise

def capture_screenshot(url):
    """Capture screenshot of a website."""
    if not url:
        return None
        
    print(f"\nAttempting to capture screenshot for: {url}")
    driver = None
    
    try:
        # Ensure screenshots directory exists
        os.makedirs('screenshots', exist_ok=True)
        
        # Get driver
        driver = get_driver()
        
        try:
            print(f"Navigating to URL: {url}")
            driver.get(url)
            time.sleep(2)  # Wait for page load
            
            print("Taking screenshot...")
            screenshot = driver.get_screenshot_as_png()
            
            if not screenshot:
                print("Screenshot capture returned None")
                return None
                
            print("Processing screenshot...")
            img = Image.open(io.BytesIO(screenshot))
            
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshots/{urlparse(url).netloc}_{timestamp}.png"
            img.save(filename, format='PNG', optimize=True, quality=95)
            print(f"Screenshot saved to: {filename}")
            
            # Create thumbnail
            thumb = img.copy()
            thumb.thumbnail((200, 200))
            
            # Convert to base64
            print("Converting to base64...")
            full_buffer = io.BytesIO()
            thumb_buffer = io.BytesIO()
            
            img.save(full_buffer, format='PNG', optimize=True, quality=95)
            thumb.save(thumb_buffer, format='PNG', optimize=True, quality=85)
            
            base64_screenshot = base64.b64encode(full_buffer.getvalue()).decode('utf-8')
            base64_thumbnail = base64.b64encode(thumb_buffer.getvalue()).decode('utf-8')
            
            print("Screenshot processing completed successfully")
            return {
                'full': base64_screenshot,
                'thumbnail': base64_thumbnail,
                'filename': filename
            }
            
        except Exception as e:
            print(f"Error capturing screenshot: {str(e)}")
            return None
            
    except Exception as e:
        print(f"Error in capture_screenshot: {str(e)}")
        return None

def get_contact_links(soup, base_url):
    """Extract potential contact page links."""
    contact_links = set()
    contact_keywords = ['contact', 'about', 'about-us', 'about us', 'kontakt', 'contacto', 'contact-us']
    
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        text = link.get_text().lower()
        
        # Check if the link text or URL contains contact-related keywords
        if any(keyword in href or keyword in text for keyword in contact_keywords):
            full_url = urljoin(base_url, href)
            if full_url.startswith(('http://', 'https://')):
                contact_links.add(full_url)
    
    return list(contact_links)[:3]  # Limit to top 3 most likely contact pages

def clean_email(email):
    """Clean and validate an email address."""
    # Remove spaces and common obfuscation
    email = re.sub(r'\s+', '', email)
    email = email.replace('[at]', '@').replace('(at)', '@')
    email = email.replace('[dot]', '.').replace('(dot)', '.')
    email = email.replace('mailto:', '')
    email = unquote(email)  # Handle URL encoding
    
    # Basic email pattern for validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return email.lower()
    return None

def extract_emails_from_text(text):
    """Extract emails using multiple patterns."""
    emails = set()
    
    patterns = [
        # Standard email pattern
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        # Pattern for emails with special characters
        r'[a-zA-Z0-9._%+-]+[\s]*(?:@|\\u0040|\[at\]|\(at\))[\s]*[a-zA-Z0-9.-]+[\s]*(?:\.|\[dot\]|\(dot\))[\s]*[a-zA-Z]{2,}',
        # Pattern for "mailto:" links (with or without spaces)
        r'mailto:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        # Pattern for encoded email addresses
        r'[a-zA-Z0-9._%+-]+\s*(?:\[|%40|&#64;|&64;)\s*[a-zA-Z0-9.-]+\s*(?:\.|&#46;|&46;)\s*[a-zA-Z]{2,}'
    ]
    
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        for email in found:
            if isinstance(email, tuple):
                email = email[0]  # Handle groups in regex
            cleaned = clean_email(email)
            if cleaned:
                emails.add(cleaned)
    
    return list(emails)

def extract_emails_from_page(url, soup=None):
    """Extract emails from a webpage including its source code."""
    emails = set()
    
    try:
        if not soup:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check elements with email-related classes or IDs
        email_indicators = ['email', 'mail', 'e-mail', 'contact']
        for indicator in email_indicators:
            # Find elements by class
            for element in soup.find_all(class_=lambda x: x and indicator in x.lower()):
                emails.update(extract_emails_from_text(str(element)))
            
            # Find elements by ID
            for element in soup.find_all(id=lambda x: x and indicator in x.lower()):
                emails.update(extract_emails_from_text(str(element)))
        
        # Check mailto links specifically
        for link in soup.find_all('a', href=lambda x: x and 'mailto:' in x.lower()):
            href = link.get('href', '')
            if href:
                cleaned = clean_email(href)
                if cleaned:
                    emails.add(cleaned)
        
        # Get all text content
        text_content = soup.get_text()
        emails.update(extract_emails_from_text(text_content))
        
        # Check source code for hidden emails
        source_code = str(soup)
        emails.update(extract_emails_from_text(source_code))
        
        # Check specific elements that might contain emails
        for element in soup.find_all(['a', 'p', 'div', 'span', 'strong', 'li']):
            # Check element text
            if element.string:
                emails.update(extract_emails_from_text(element.string))
            
            # Check element attributes
            for attr in ['href', 'data-email', 'title', 'alt', 'content']:
                if element.has_attr(attr):
                    emails.update(extract_emails_from_text(element[attr]))
        
        return list(emails)
    except Exception as e:
        print(f"Error extracting emails from {url}: {str(e)}")
        return []

def extract_emails(url):
    """Extract emails from a website and its contact pages."""
    all_emails = set()
    
    try:
        # Get the main page
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract emails from main page
        main_page_emails = extract_emails_from_page(url, soup)
        all_emails.update(main_page_emails)
        
        # Get contact page links
        contact_links = get_contact_links(soup, url)
        
        # Extract emails from contact pages using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            contact_page_emails = list(executor.map(extract_emails_from_page, contact_links))
            for emails in contact_page_emails:
                all_emails.update(emails)
        
        return list(all_emails)
    except Exception as e:
        print(f"Error processing website {url}: {str(e)}")
        return []

def clean_website_url(url):
    """Clean and validate website URL."""
    if not url:
        return None
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except:
        return None

def search_places(location, keyword, page_token=None):
    """Search places using Places API v2."""
    try:
        # Check if API key is available
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            print("Error: Google Places API key not found in environment variables")
            return None

        print(f"\n=== Starting search for '{keyword}' in '{location}' ===")
        
        # First, get location coordinates using Geocoding API
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={quote(location)}&key={api_key}"
        
        try:
            geocode_response = requests.get(geocode_url)
            geocode_response.raise_for_status()
            geocode_data = geocode_response.json()
            
            if not geocode_data.get('results'):
                print(f"No geocoding results found for location: {location}")
                print(f"Geocoding API response: {geocode_data}")
                return None
                
            location_data = geocode_data['results'][0]['geometry']['location']
            center_lat, center_lng = location_data['lat'], location_data['lng']
            print(f"Found coordinates: {center_lat}, {center_lng}")
            
            # Define search points around the center location
            radius = 5000  # 5km radius
            search_points = [
                (center_lat, center_lng),  # Center
                (center_lat + 0.05, center_lng),  # North
                (center_lat - 0.05, center_lng),  # South
                (center_lat, center_lng + 0.05),  # East
                (center_lat, center_lng - 0.05),  # West
            ]
            
            all_results = []
            seen_place_ids = set()
            
            # Search places using Places API v2 for each point
            for lat, lng in search_points:
                search_url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.websiteUri,places.internationalPhoneNumber,places.nationalPhoneNumber"
                }
                
                data = {
                    "textQuery": f"{keyword} in {location}",
                    "locationBias": {
                        "circle": {
                            "center": {
                                "latitude": lat,
                                "longitude": lng
                            },
                            "radius": float(radius)
                        }
                    },
                    "maxResultCount": 5
                }
                
                if page_token:
                    data["pageToken"] = page_token
                
                try:
                    print(f"\nMaking Places API request for coordinates: {lat}, {lng}")
                    print(f"Request data: {json.dumps(data, indent=2)}")
                    
                    response = requests.post(search_url, headers=headers, json=data)
                    print(f"Response status code: {response.status_code}")
                    
                    if response.status_code != 200:
                        print(f"Places API Error for point ({lat}, {lng}): {response.status_code}")
                        print(f"Error response: {response.text}")
                        continue
                    
                    result = response.json()
                    
                    # Add unique places to results
                    if 'places' in result:
                        print(f"Found {len(result['places'])} places at this point")
                        for place in result['places']:
                            if place.get('id') not in seen_place_ids:
                                seen_place_ids.add(place.get('id'))
                                all_results.append(place)
                    else:
                        print("No places found in the response")
                        print(f"Response content: {json.dumps(result, indent=2)}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"Request error at point ({lat}, {lng}): {str(e)}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"Error response: {e.response.text}")
                    continue
                except Exception as e:
                    print(f"Unexpected error at point ({lat}, {lng}): {str(e)}")
                    continue
                
                time.sleep(1)  # Wait between requests to different points
            
            print(f"\nTotal unique results found: {len(all_results)}")
            return {"places": all_results}  # Return all unique results
            
        except requests.exceptions.RequestException as e:
            print(f"Geocoding API request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error response: {e.response.text}")
            return None
            
    except Exception as e:
        print(f"Unexpected error in search_places: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-csrf-token')
def get_csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})

@app.route('/search', methods=['POST'])
@csrf.exempt
def search():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        location = data.get('location')
        keyword = data.get('keyword')
        
        if not location or not keyword:
            return jsonify({'error': 'Location and keyword are required'}), 400
        
        print(f"\nProcessing search request for {keyword} in {location}")
        
        # Search for places
        places_result = search_places(location, keyword)
        if not places_result:
            return jsonify({'error': 'No results found'}), 404
        
        businesses = []
        
        # Process places without screenshots first
        for place in places_result.get('places', []):
            try:
                business = {
                    'name': place.get('displayName', {}).get('text', ''),
                    'website': clean_website_url(place.get('websiteUri', '')),
                    'address': place.get('formattedAddress', ''),
                    'phone': place.get('internationalPhoneNumber', '') or place.get('nationalPhoneNumber', ''),
                    'screenshot': None
                }
                businesses.append(business)
                print(f"Added business: {business['name']} ({business['website']})")
            except Exception as e:
                print(f"Error processing place: {str(e)}")
                continue
        
        # Process screenshots sequentially
        businesses_with_websites = [b for b in businesses if b['website']]
        completed_screenshots = 0
        
        print(f"\nProcessing screenshots for {len(businesses_with_websites)} businesses with websites")
        
        for business in businesses_with_websites:
            try:
                screenshot = capture_screenshot(business['website'])
                if screenshot:
                    business['screenshot'] = screenshot
                    completed_screenshots += 1
                    print(f"Screenshot captured successfully for {business['website']}")
                else:
                    print(f"Failed to capture screenshot for {business['website']}")
            except Exception as e:
                print(f"Error capturing screenshot for {business['website']}: {str(e)}")
        
        print(f"\nCompleted processing {completed_screenshots} screenshots out of {len(businesses_with_websites)} websites")
        
        return jsonify({
            'success': True,
            'businesses': businesses,
            'screenshots_completed': completed_screenshots,
            'total_businesses': len(businesses)
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad Request'}), 400

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/download-csv')
def download_csv():
    data = request.args.get('data')
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    businesses = json.loads(data)
    df = pd.DataFrame(businesses)
    
    # Convert DataFrame to CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    
    # Create the response
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'business_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.teardown_appcontext
def cleanup(exception=None):
    """Clean up resources when the application context ends."""
    if hasattr(thread_local, "driver"):
        try:
            thread_local.driver.quit()
            print("WebDriver cleaned up successfully")
        except Exception as e:
            print(f"Error cleaning up WebDriver: {str(e)}")
        finally:
            thread_local.driver = None

if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        # Ensure cleanup on application exit
        cleanup()
