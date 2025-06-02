from flask import Flask, render_template, request, jsonify, send_file
from flask_wtf.csrf import CSRFProtect
import requests
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
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Debug print for API key
api_key = os.getenv('GOOGLE_PLACES_API_KEY')
if api_key:
    print(f"API Key loaded (first 10 chars): {api_key[:10]}...")
else:
    print("Warning: No API key found in .env file")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
csrf = CSRFProtect(app)

# Configure requests session with retries and timeouts
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

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
    # First, get location coordinates using Geocoding API
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={quote(location)}&key={os.getenv('GOOGLE_PLACES_API_KEY')}"
    
    try:
        geocode_response = requests.get(geocode_url)
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()
        
        if not geocode_data.get('results'):
            return None
            
        location_data = geocode_data['results'][0]['geometry']['location']
        center_lat, center_lng = location_data['lat'], location_data['lng']
        
        # Define multiple search points around the center location
        radius = 50000  # 5km radius
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
                "X-Goog-Api-Key": os.getenv('GOOGLE_PLACES_API_KEY'),
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.websiteUri,places.internationalPhoneNumber,places.nationalPhoneNumber,nextPageToken"
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
                "maxResultCount": 300
            }
            
            if page_token:
                data["pageToken"] = page_token
            
            try:
                response = requests.post(search_url, headers=headers, json=data)
                if response.status_code != 200:
                    print(f"Places API Error for point ({lat}, {lng}): {response.status_code}")
                    print(f"Response: {response.text}")
                    continue
                
                result = response.json()
                
                # Add unique places to results
                if 'places' in result:
                    for place in result['places']:
                        if place.get('id') not in seen_place_ids:
                            seen_place_ids.add(place.get('id'))
                            all_results.append(place)
                
                # Handle pagination if available
                if 'nextPageToken' in result and len(all_results) < 100:
                    time.sleep(2)  # Wait before making the next request
                    next_page_results = search_places(location, keyword, result['nextPageToken'])
                    if next_page_results and 'places' in next_page_results:
                        for place in next_page_results['places']:
                            if place.get('id') not in seen_place_ids:
                                seen_place_ids.add(place.get('id'))
                                all_results.append(place)
                
            except Exception as e:
                print(f"Error searching at point ({lat}, {lng}): {str(e)}")
                continue
            
            time.sleep(1)  # Wait between requests to different points
        
        return {"places": all_results[:500]}  # Return up to 100 unique results
        
    except Exception as e:
        print(f"Error searching places: {str(e)}")
        if isinstance(e, requests.exceptions.RequestException) and e.response:
            print(f"Response: {e.response.text}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    location = data.get('location')
    keyword = data.get('keyword')
    
    if not location or not keyword:
        return jsonify({'error': 'Location and keyword are required'}), 400
    
    try:
        # Search for places
        places_result = search_places(location, keyword)
        if not places_result:
            return jsonify({'error': 'No results found'}), 404
        
        businesses = []
        
        # Process places
        for place in places_result.get('places', []):
            business = {
                'name': place.get('displayName', {}).get('text', ''),
                'website': clean_website_url(place.get('websiteUri', '')),
                'address': place.get('formattedAddress', ''),
                'has_website': bool(place.get('websiteUri')),
                'phone': place.get('internationalPhoneNumber', '') or place.get('nationalPhoneNumber', ''),
                'emails': []
            }
            
            # Uncomment these lines to enable email scraping
            # if business['website']:
            #     business['emails'] = extract_emails(business['website'])
            
            businesses.append(business)
        
        if not businesses:
            return jsonify({'error': 'No businesses found'}), 404
            
        return jsonify({
            'success': True,
            'businesses': businesses
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    app.run(debug=True)
