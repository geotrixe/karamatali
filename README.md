# Karamat Ali 

**WordPress | Shopify Developer**

📧 geotrixe@gmail.com  
📱 +923004588711

Experienced web developer specializing in **WordPress** and **Shopify**. Skilled in creating eCommerce solutions with hands-on expertise in **Shopify Liquid**, **HTML**, **CSS**, **Bootstrap**, **jQuery**, and **PHP**. Background in **PPC**, **SEO**, and **Email Marketing**, with extensive knowledge of **Magento 1 and 2**, **Figma to Template Conversion**, and **PSD to WordPress and Shopify templates**.

---

## 🛠️ Technical Skills

- **Languages/Technologies:** HTML, CSS, jQuery, Bootstrap, JavaScript, PHP
- **Frameworks/Platforms:** Shopify Liquid, WordPress, Magento
- **Design Tools:** Figma, Photoshop
- **E-commerce:** Shopify Partner, WooCommerce
- **Marketing/SEO:** PPC, SEO, Email Marketing

---

## 🌐 Professional Links

### Shopify Projects
- [choputaeats.com](https://choputaeats.com)
- [drinkrenude.com](https://drinkrenude.com)
- [mfcoffroad.com](https://mfcoffroad.com)
- [causeforelegance.com](https://causeforelegance.com)
- [thediamondoak.com](https://thediamondoak.com)
- [midvalebox.com](https://midvalebox.com)
- [shopbeautyandthebabe.com](https://shopbeautyandthebabe.com)

### WordPress Projects
- [mdnewsline.com](https://mdnewsline.com)
- [stockKonnect.co](https://stockKonnect.co)
- [almuslimtravel.co.uk](https://almuslimtravel.co.uk)
- [rytondental.com](https://rytondental.com)
- [tanzeem.org](https://tanzeem.org)
- [polarcream.com](https://polarcream.com)

---

## 💼 Work Experience

**Senior Shopify Developer**  
*09/2023 - Present | Mushrp, Lahore*  
- Lead development on Shopify and WordPress projects.
- Created high-quality, user-friendly eCommerce sites on Shopify.
- Expertise in Shopify theme customization and advanced functionality.

**Shopify Developer**  
*09/2022 - 08/2023 | Napollo Software Design LLC, Lahore*  
- Developed websites on Shopify, WordPress, Squarespace, WIX, and WebFlow.
- Customized Shopify themes and implemented advanced features.
- Strong focus on HTML, CSS, JavaScript integration with third-party services.

**E-commerce Web Developer**  
*08/2019 - 08/2022 | Cutting Edge Projects, UK*  
- Developed eCommerce stores on Shopify Liquid, Magento 2, WooCommerce.
- Managed social media ads, SEO, PPC, and performance reporting.
- Provided continuous support, creating responsive and visually appealing designs.

---

## 🎓 Education

**Master of Computer Science (MCS)**  
*Lahore Garrison University*

---

### 👨‍💻 About Me

Experienced in building robust, user-friendly eCommerce websites with **6+ years** in Shopify development and **proven expertise in theme customization**. Proficient in managing and optimizing digital marketing campaigns, SEO, and PPC to drive traffic and conversions. Well-versed in front-end and back-end development with a focus on creating seamless, engaging user experiences.

---

### 📫 Contact
- **Email:** [geotrixe@gmail.com](mailto:geotrixe@gmail.com)
- **Phone:** +923004588711

# Business Data Scraper

A Python web application that searches for businesses using the Google Places API and scrapes their websites for contact information.

## Features

- 🔍 Search businesses by location and keyword
- 🌐 Automatically detects and categorizes businesses with/without websites
- 📧 Scrapes email addresses from business websites
- 📊 Clean, responsive UI with filtering options
- 📥 Export results to CSV
- 🌙 Dark mode support

## Prerequisites

- Python 3.8 or higher
- Google Places API key

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following content:
```
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
SECRET_KEY=your_flask_secret_key_here
```

Replace `your_google_places_api_key_here` with your actual Google Places API key.

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Enter a location and business type to search

4. View results in the tabbed interface:
   - All Results
   - With Website
   - Without Website
   - Emails Found

5. Download results as CSV using the download button

## Features

### Search
- Location-based search using Google Places API
- Keyword filtering for business types
- 5km radius search from specified location

### Data Collection
- Business name
- Address
- Website URL (if available)
- Email addresses (scraped from website)

### UI Features
- Responsive Bootstrap design
- Dark mode toggle
- Progress indicator during searches
- Tabbed interface for filtered views
- Sortable tables
- Toast notifications for status updates

### Export
- CSV export with all collected data
- Timestamp-based file naming

## Rate Limiting and Error Handling

- Timeout handling for website scraping
- Error notifications via toast messages
- Graceful handling of API limits

## Security

- CSRF protection enabled
- Environment variables for sensitive data
- Secure file downloads

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
