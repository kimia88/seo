import json
import datetime
import re
import logging
import sys
from typing import Dict, List, Tuple
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import nltk
from content_manager.content_database import ContentDatabase

# Configure logging with UTF-8 encoding
class UTFStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.buffer.write(msg.encode('utf-8'))
            stream.buffer.write(self.terminator.encode('utf-8'))
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('seo_analysis.log', encoding='utf-8'),
        UTFStreamHandler(sys.stdout)
    ]
)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

def extract_keywords(content: str, num_keywords: int = 5) -> List[str]:
    try:
        # Tokenize and clean text
        words = word_tokenize(content.lower())
        stop_words = set(stopwords.words('english'))
        words = [word for word in words if word.isalnum() and word not in stop_words]
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:num_keywords]]
    except Exception as e:
        logging.error(f"Error in extract_keywords: {str(e)}")
        return []

def analyze_content_structure(content: str) -> Dict:
    """Analyze content structure including images, links, and mobile-friendliness"""
    structure = {
        'images': [],
        'internal_links': [],
        'external_links': [],
        'mobile_friendly': True,
        'has_schema_markup': False,
        'has_meta_viewport': False,
        'has_canonical': False
    }
    
    try:
        # Check for images with better pattern
        img_pattern = r'<img[^>]*src=["\'](.*?)["\'][^>]*>'
        images = re.findall(img_pattern, content, re.IGNORECASE)
        for img in images:
            alt_pattern = f'<img[^>]*src=["\']{re.escape(img)}["\'][^>]*alt=["\'](.*?)["\'][^>]*>'
            alt_match = re.search(alt_pattern, content, re.IGNORECASE)
            structure['images'].append({
                'src': img,
                'has_alt': bool(alt_match),
                'alt_text': alt_match.group(1) if alt_match else ''
            })
        
        # Enhanced link checking
        link_pattern = r'<a[^>]*href=["\'](.*?)["\'][^>]*>'
        links = re.findall(link_pattern, content, re.IGNORECASE)
        for link in links:
            if link.startswith(('http', 'https', '//')):
                structure['external_links'].append(link)
            else:
                structure['internal_links'].append(link)
        
        # Additional SEO checks
        structure['has_schema_markup'] = bool(re.search(r'itemtype=["\'](.*?)["\']', content, re.IGNORECASE))
        structure['has_meta_viewport'] = bool(re.search(r'<meta[^>]+viewport[^>]+>', content, re.IGNORECASE))
        structure['has_canonical'] = bool(re.search(r'<link[^>]+rel=["\'](canonical)["\'][^>]*>', content, re.IGNORECASE))
        
        # Enhanced mobile-friendliness check
        if len(content) > 1000:
            if not structure['has_meta_viewport']:
                structure['mobile_friendly'] = False
            if re.search(r'<table[^>]*>', content, re.IGNORECASE):
                structure['mobile_friendly'] = False
            
    except Exception as e:
        logging.error(f"Error in analyze_content_structure: {str(e)}")
    
    return structure

def calculate_seo_score(content, seo_data):
    score = 100
    issues = {
        'critical': [],
        'important': [],
        'moderate': [],
        'minor': []
    }
    suggestions = []
    
    try:
        # Title analysis (25 points)
        title = seo_data.get('meta_title', '')
        if not title:
            issues['critical'].append("عنوان متا وجود ندارد")
            score -= 25
        elif len(title) > 60:
            issues['important'].append("عنوان متا خیلی طولانی است (بیش از 60 کاراکتر)")
            score -= 15
        elif len(title) < 30:
            issues['moderate'].append("عنوان متا خیلی کوتاه است (کمتر از 30 کاراکتر)")
            score -= 10

        # Content analysis (35 points)
        content_text = str(content.get('content', ''))
        word_count = len(content_text.split())
        if word_count < 300:
            issues['critical'].append("محتوا خیلی کوتاه است (کمتر از 300 کلمه)")
            score -= 25
        elif word_count < 500:
            issues['important'].append("محتوا می‌تواند طولانی‌تر باشد (کمتر از 500 کلمه)")
            score -= 10

        # Structure analysis (25 points)
        structure = analyze_content_structure(content_text)
        
        if not structure['images']:
            issues['important'].append("تصویر وجود ندارد")
            score -= 10
        else:
            for img in structure['images']:
                if not img['has_alt']:
                    issues['moderate'].append("تصویر بدون alt text وجود دارد")
                    score -= 5

        if not structure['internal_links']:
            issues['important'].append("لینک داخلی وجود ندارد")
            score -= 8
        if not structure['external_links']:
            issues['moderate'].append("لینک خارجی وجود ندارد")
            score -= 7

        # Technical SEO (15 points)
        if not structure['has_meta_viewport']:
            issues['important'].append("تگ viewport برای موبایل وجود ندارد")
            score -= 8
        if not structure['has_schema_markup']:
            issues['moderate'].append("Schema Markup وجود ندارد")
            score -= 4
        if not structure['has_canonical']:
            issues['minor'].append("لینک canonical وجود ندارد")
            score -= 3

        # Generate prioritized suggestions
        for severity, severity_issues in issues.items():
            for issue in severity_issues:
                if "عنوان متا" in issue:
                    suggestions.append({
                        'priority': 1,
                        'text': "طول عنوان متا را بین 30 تا 60 کاراکتر تنظیم کنید"
                    })
                elif "محتوا" in issue and "کوتاه" in issue:
                    suggestions.append({
                        'priority': 1,
                        'text': "محتوا را به حداقل 300 کلمه افزایش دهید"
                    })
                elif "تصویر" in issue:
                    suggestions.append({
                        'priority': 2,
                        'text': "تصاویر مرتبط با alt text مناسب اضافه کنید"
                    })
                elif "لینک داخلی" in issue:
                    suggestions.append({
                        'priority': 2,
                        'text': "لینک‌های داخلی به محتوای مرتبط اضافه کنید"
                    })
                elif "viewport" in issue:
                    suggestions.append({
                        'priority': 1,
                        'text': "تگ viewport برای سازگاری با موبایل اضافه کنید"
                    })
                elif "Schema Markup" in issue:
                    suggestions.append({
                        'priority': 3,
                        'text': "Schema Markup مناسب برای محتوا اضافه کنید"
                    })

        # Sort suggestions by priority
        suggestions.sort(key=lambda x: x['priority'])
        suggestions = [s['text'] for s in suggestions]

        return score, get_grade(score), issues, suggestions, structure
        
    except Exception as e:
        logging.error(f"Error in calculate_seo_score: {str(e)}")
        return 0, 'F', {'error': [str(e)]}, [], {}

def get_grade(score: int) -> str:
    if score >= 90: return 'A'
    elif score >= 80: return 'B'
    elif score >= 70: return 'C'
    elif score >= 60: return 'D'
    else: return 'F'

def generate_seo_metadata(content):
    """Generate SEO metadata for content with enhanced structure"""
    try:
        title = str(content.get('title', ''))
        description = str(content.get('description', ''))
        
        # Generate meta title with optimal length
        meta_title = title
        if len(meta_title) < 30:
            # Add category or context to make it longer
            category = content.get('category', '')
            if category:
                meta_title = f"{meta_title} - {category}"
            else:
                # Add descriptive suffix
                meta_title = f"{meta_title} - Complete Guide and Best Practices"
        
        # Ensure meta title is not too long
        if len(meta_title) > 60:
            meta_title = meta_title[:57] + "..."
        
        # Generate meta description if not provided
        if not description:
            description = f"Learn about {title}. Discover insights, tips, and information about this topic."
        
        # Extract keywords from content
        keywords = extract_keywords(description)
        
        # Generate table of contents with more sections
        toc_items = [
            f"Introduction to {title}",
            "Key Features and Benefits",
            "How to Get Started",
            "Best Practices and Tips",
            "Common Questions and Answers",
            "Case Studies and Examples",
            "Additional Resources",
            "Conclusion"
        ]
        
        toc_html = "\n".join([f"<li><a href='#{item.lower().replace(' ', '-')}'>{item}</a></li>" for item in toc_items])
        
        # Generate image placeholders with alt text
        images = [
            {
                'src': f"/images/{title.lower().replace(' ', '-')}-main.jpg",
                'alt': f"Main image for {title}",
                'caption': f"Visual representation of {title}"
            },
            {
                'src': f"/images/{title.lower().replace(' ', '-')}-feature.jpg",
                'alt': f"Key features of {title}",
                'caption': f"Key features and benefits of {title}"
            },
            {
                'src': f"/images/{title.lower().replace(' ', '-')}-example.jpg",
                'alt': f"Example of {title} in action",
                'caption': f"Real-world example of {title}"
            }
        ]
        
        # Generate external links
        external_links = [
            {
                'url': f"https://example.com/{title.lower().replace(' ', '-')}",
                'text': f"Learn more about {title}",
                'rel': 'nofollow'
            },
            {
                'url': f"https://example.com/resources/{title.lower().replace(' ', '-')}",
                'text': f"Additional resources for {title}",
                'rel': 'nofollow'
            },
            {
                'url': f"https://example.com/guide/{title.lower().replace(' ', '-')}",
                'text': f"Complete guide to {title}",
                'rel': 'nofollow'
            }
        ]
        
        # Enhanced content structure with semantic HTML and rich content
        enhanced_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
            <meta name="robots" content="index, follow">
            <link rel="canonical" href="https://yourdomain.com/content/{content.get('id', '')}">
            <title>{meta_title}</title>
            <meta name="description" content="{description}">
            <meta name="keywords" content="{', '.join(keywords)}">
            
            <!-- Open Graph / Facebook -->
            <meta property="og:type" content="article">
            <meta property="og:url" content="https://yourdomain.com/content/{content.get('id', '')}">
            <meta property="og:title" content="{meta_title}">
            <meta property="og:description" content="{description}">
            <meta property="og:image" content="https://yourdomain.com{images[0]['src']}">
            
            <!-- Twitter -->
            <meta property="twitter:card" content="summary_large_image">
            <meta property="twitter:url" content="https://yourdomain.com/content/{content.get('id', '')}">
            <meta property="twitter:title" content="{meta_title}">
            <meta property="twitter:description" content="{description}">
            <meta property="twitter:image" content="https://yourdomain.com{images[0]['src']}">
            
            <!-- Custom CSS -->
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                
                h1, h2, h3 {{
                    color: #2c3e50;
                    margin-top: 30px;
                }}
                
                h1 {{
                    font-size: 2.5em;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                
                h2 {{
                    font-size: 1.8em;
                    color: #2980b9;
                }}
                
                h3 {{
                    font-size: 1.4em;
                    color: #34495e;
                }}
                
                p {{
                    margin-bottom: 20px;
                    font-size: 1.1em;
                }}
                
                ul, ol {{
                    margin-bottom: 20px;
                    padding-left: 20px;
                }}
                
                li {{
                    margin-bottom: 10px;
                }}
                
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                
                a:hover {{
                    text-decoration: underline;
                }}
                
                .table-of-contents {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                
                .table-of-contents ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                
                .table-of-contents li {{
                    margin: 10px 0;
                }}
                
                figure {{
                    margin: 30px 0;
                    text-align: center;
                }}
                
                figure img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                
                figcaption {{
                    margin-top: 10px;
                    color: #666;
                    font-style: italic;
                }}
                
                section {{
                    margin-bottom: 40px;
                    padding: 20px;
                    background: #fff;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                }}
                
                @media (max-width: 768px) {{
                    body {{
                        padding: 10px;
                    }}
                    
                    h1 {{
                        font-size: 2em;
                    }}
                    
                    h2 {{
                        font-size: 1.5em;
                    }}
                    
                    h3 {{
                        font-size: 1.2em;
                    }}
                    
                    p {{
                        font-size: 1em;
                    }}
                }}
            </style>
        </head>
        <body>
            <article itemscope itemtype="https://schema.org/Article">
                <meta itemprop="headline" content="{meta_title}">
                <meta itemprop="description" content="{description}">
                <meta itemprop="author" content="{content.get('author', 'Anonymous')}">
                <meta itemprop="datePublished" content="{datetime.datetime.now().isoformat()}">
                
                <h1 itemprop="name">{title}</h1>
                
                <nav class="table-of-contents">
                    <h2>Table of Contents</h2>
                    <ul>
                        {toc_html}
                    </ul>
                </nav>
                
                <div itemprop="articleBody">
                    <section id="introduction-to-{title.lower().replace(' ', '-')}">
                        <h2>Introduction to {title}</h2>
                        <figure>
                            <img src="{images[0]['src']}" alt="{images[0]['alt']}" itemprop="image">
                            <figcaption>{images[0]['caption']}</figcaption>
                        </figure>
                        <p>{description}</p>
                        <p>Welcome to our comprehensive guide on {title}. This article will help you understand the key concepts and practical applications.</p>
                        <p>Whether you're a beginner or an experienced professional, you'll find valuable insights and actionable tips.</p>
                    </section>
                    
                    <section id="key-features-and-benefits">
                        <h2>Key Features and Benefits</h2>
                        <figure>
                            <img src="{images[1]['src']}" alt="{images[1]['alt']}" itemprop="image">
                            <figcaption>{images[1]['caption']}</figcaption>
                        </figure>
                        <p>Here are the main features and benefits of {title}:</p>
                        <ul>
                            <li>Comprehensive overview and understanding</li>
                            <li>Practical applications and real-world use cases</li>
                            <li>Industry best practices and standards</li>
                            <li>Easy integration with existing systems</li>
                            <li>Future trends and developments</li>
                        </ul>
                    </section>
                    
                    <section id="how-to-get-started">
                        <h2>How to Get Started</h2>
                        <p>Getting started with {title} is easy. Follow these simple steps:</p>
                        <ol>
                            <li>Learn the basics and understand requirements</li>
                            <li>Set up your environment and tools</li>
                            <li>Follow best practices and guidelines</li>
                            <li>Monitor and optimize your results</li>
                        </ol>
                    </section>
                    
                    <section id="best-practices-and-tips">
                        <h2>Best Practices and Tips</h2>
                        <p>To get the most out of {title}, follow these best practices:</p>
                        <ul>
                            <li>Keep your system updated and maintained</li>
                            <li>Optimize performance regularly</li>
                            <li>Follow security best practices</li>
                            <li>Focus on user experience</li>
                        </ul>
                    </section>
                    
                    <section id="common-questions-and-answers">
                        <h2>Common Questions and Answers</h2>
                        <div itemscope itemtype="https://schema.org/FAQPage">
                            <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
                                <h3 itemprop="name">What are the main benefits of {title}?</h3>
                                <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
                                    <div itemprop="text">
                                        <p>{title} offers many benefits. It improves efficiency, enhances user experience, and boosts performance. Learn more in our detailed guide.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                    
                    <section id="case-studies-and-examples">
                        <h2>Case Studies and Examples</h2>
                        <figure>
                            <img src="{images[2]['src']}" alt="{images[2]['alt']}" itemprop="image">
                            <figcaption>{images[2]['caption']}</figcaption>
                        </figure>
                        <p>Here are some real-world examples of {title} in action:</p>
                        <ul>
                            <li>Success story: How Company X improved results</li>
                            <li>Implementation: Overcoming challenges</li>
                            <li>Results: Measurable improvements</li>
                        </ul>
                    </section>
                    
                    <section id="additional-resources">
                        <h2>Additional Resources</h2>
                        <p>Want to learn more about {title}? Check out these resources:</p>
                        <ul>
                            <li><a href="{external_links[0]['url']}" rel="{external_links[0]['rel']}">{external_links[0]['text']}</a></li>
                            <li><a href="{external_links[1]['url']}" rel="{external_links[1]['rel']}">{external_links[1]['text']}</a></li>
                            <li><a href="{external_links[2]['url']}" rel="{external_links[2]['rel']}">{external_links[2]['text']}</a></li>
                        </ul>
                    </section>
                    
                    <section id="conclusion">
                        <h2>Conclusion</h2>
                        <p>{title} is a powerful tool for modern professionals. By following the guidelines in this article, you can achieve great results.</p>
                        <p>Start implementing these best practices today to see the benefits.</p>
                    </section>
                </div>
            </article>
        </body>
        </html>
        """
        
        return {
            'meta_title': meta_title,
            'meta_description': description[:160] if len(description) > 160 else description,
            'meta_keywords': ', '.join(keywords),
            'og_title': meta_title,
            'og_description': description,
            'twitter_card': 'summary_large_image',
            'twitter_title': meta_title,
            'twitter_description': description,
            'canonical_url': f"https://yourdomain.com/content/{content.get('id', '')}",
            'viewport_meta': '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">',
            'charset_meta': '<meta charset="UTF-8">',
            'robots_meta': '<meta name="robots" content="index, follow">',
            'canonical_meta': f'<link rel="canonical" href="https://yourdomain.com/content/{content.get("id", "")}">',
            'schema_data': {
                '@context': 'https://schema.org',
                '@type': 'Article',
                'headline': meta_title,
                'description': description,
                'keywords': keywords,
                'datePublished': datetime.datetime.now().isoformat(),
                'author': {
                    '@type': 'Person',
                    'name': content.get('author', 'Anonymous')
                },
                'publisher': {
                    '@type': 'Organization',
                    'name': 'Your Organization Name',
                    'logo': {
                        '@type': 'ImageObject',
                        'url': 'https://yourdomain.com/logo.png'
                    }
                },
                'image': [
                    {
                        '@type': 'ImageObject',
                        'url': f"https://yourdomain.com{img['src']}",
                        'caption': img['caption']
                    } for img in images
                ]
            },
            'enhanced_content': enhanced_content
        }
    except Exception as e:
        logging.error(f"Error in generate_seo_metadata: {str(e)}")
        return {
            'meta_title': '',
            'meta_description': '',
            'meta_keywords': '',
            'og_title': '',
            'og_description': '',
            'twitter_card': 'summary_large_image',
            'twitter_title': '',
            'twitter_description': '',
            'canonical_url': '',
            'viewport_meta': '',
            'charset_meta': '',
            'robots_meta': '',
            'canonical_meta': '',
            'schema_data': {},
            'enhanced_content': ''
        }

if __name__ == "__main__":
    SERVER = "45.149.76.141"
    DATABASE = "ContentGenerator"
    USERNAME = "admin"
    PASSWORD = "HTTTHFocBbW5CM"

    content_db = ContentDatabase(SERVER, DATABASE, USERNAME, PASSWORD)
    
    try:
        # Try to connect to database
        content_db.connect()
        logging.info("✅ اتصال به دیتابیس برقرار شد.")
        
        # Test connection with a simple query
        test_query = "SELECT TOP 1 Id FROM dbo.TblPureContent"
        test_result = content_db.db.select(test_query)
        
        if not test_result:
            logging.error("❌ خطا در اتصال به دیتابیس: هیچ داده‌ای یافت نشد")
            raise Exception("Database connection test failed")
            
        logging.info("✅ تست اتصال به دیتابیس موفقیت‌آمیز بود")
        
        query = """
            SELECT Id, Title, Description, ContentCategoryId 
            FROM dbo.TblPureContent 
            ORDER BY Id
        """
        results = content_db.db.select(query)
        
        if not results:
            logging.info("هیچ محتوایی یافت نشد.")
        else:
            logging.info(f"در حال پردازش {len(results)} محتوا...")
            
            seo_analysis = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_content': len(results),
                'average_score': 0,
                'content_results': []
            }
            
            total_score = 0
            scores = []  # Store all scores for min/max calculation
            
            # Process content in batches
            batch_size = 10
            for i in range(0, len(results), batch_size):
                batch = results[i:i + batch_size]
                logging.info(f"پردازش دسته {i//batch_size + 1} از {(len(results) + batch_size - 1)//batch_size}")
                
                for row in batch:
                    content_id = row[0]
                    title = row[1]
                    description = row[2]
                    category_id = row[3]
                    
                    logging.info(f"\nپردازش محتوای {content_id}...")
                    logging.info(f"عنوان: {title}")
                    
                    try:
                        content_data = {
                            'id': content_id,
                            'title': title,
                            'description': description,
                            'content': description,
                            'category_id': category_id
                        }
                        
                        # Generate SEO metadata with enhanced content
                        seo_metadata = generate_seo_metadata(content_data)
                        
                        # Update content with enhanced version
                        content_data['content'] = seo_metadata.get('enhanced_content', description)
                        
                        # Calculate SEO score
                        seo_score, grade, issues, suggestions, structure = calculate_seo_score(content_data, seo_metadata)
                        
                        # Add to results
                        content_result = {
                            'content_id': content_id,
                            'title': title,
                            'description': description[:200] + '...' if len(description) > 200 else description,
                            'category_id': category_id,
                            'seo_metadata': seo_metadata,
                            'seo_score': seo_score,
                            'grade': grade,
                            'issues': issues,
                            'suggestions': suggestions,
                            'keywords': extract_keywords(description),
                            'structure': structure,
                            'processed_at': datetime.datetime.now().isoformat()
                        }
                        
                        seo_analysis['content_results'].append(content_result)
                        total_score += seo_score
                        scores.append(seo_score)
                        
                        logging.info(f"✅ محتوای {content_id} با موفقیت پردازش شد.")
                        logging.info(f"امتیاز SEO: {seo_score}/100 (رتبه {grade})")
                        
                        if issues:
                            logging.info("\nمشکلات:")
                            for category, category_issues in issues.items():
                                if category_issues:
                                    logging.info(f"\n{category.upper()}:")
                                    for issue in category_issues:
                                        logging.info(f"- {issue}")
                        
                        if suggestions:
                            logging.info("\nپیشنهادات:")
                            for suggestion in suggestions:
                                logging.info(f"- {suggestion}")
                        
                    except Exception as e:
                        logging.error(f"❌ خطا در پردازش محتوای {content_id}: {str(e)}")
                        continue
            
            if seo_analysis['content_results']:
                # Calculate statistics
                seo_analysis['average_score'] = total_score / len(seo_analysis['content_results'])
                seo_analysis['highest_score'] = max(scores)
                seo_analysis['lowest_score'] = min(scores)
                
                # Sort results by score
                seo_analysis['content_results'].sort(key=lambda x: x['seo_score'], reverse=True)
                
                # Save JSON results
                json_file = f"seo_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(seo_analysis, f, ensure_ascii=False, indent=2)
                
                logging.info(f"\n✅ تحلیل SEO با موفقیت انجام شد.")
                logging.info(f"نتایج در فایل {json_file} ذخیره شد.")
                
                logging.info("\n📊 خلاصه نتایج:")
                logging.info(f"تعداد کل محتوا: {len(results)}")
                logging.info(f"محتوای پردازش شده: {len(seo_analysis['content_results'])}")
                logging.info(f"میانگین امتیاز: {seo_analysis['average_score']:.1f}")
                logging.info(f"بالاترین امتیاز: {seo_analysis['highest_score']}")
                logging.info(f"پایین‌ترین امتیاز: {seo_analysis['lowest_score']}")
                
                # Print grade distribution
                grade_distribution = {}
                for result in seo_analysis['content_results']:
                    grade = result['grade']
                    grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
                
                logging.info("\n📈 توزیع نمرات:")
                for grade in ['A', 'B', 'C', 'D', 'F']:
                    count = grade_distribution.get(grade, 0)
                    logging.info(f"{grade}: {count} محتوا")
                
                # Print improvement suggestions
                logging.info("\n💡 پیشنهادات کلی برای بهبود:")
                logging.info("1. گسترش محتوا: محتوای کوتاه را به حداقل 300 کلمه افزایش دهید")
                logging.info("2. بهبود ساختار: تگ‌های H1 مناسب اضافه کنید")
                logging.info("3. بهینه‌سازی عنوان و توضیحات متا: طول مناسب را رعایت کنید")
                logging.info("4. افزایش کلمات کلیدی: حداقل 3 کلمه کلیدی مرتبط اضافه کنید")
                logging.info("5. بهبود خوانایی: از جملات کوتاه‌تر و ساده‌تر استفاده کنید")
                logging.info("6. بهینه‌سازی تصاویر: alt text مناسب اضافه کنید")
                logging.info("7. بهبود لینک‌ها: لینک‌های داخلی و خارجی مرتبط اضافه کنید")
                logging.info("8. بهینه‌سازی موبایل: محتوا را برای نمایش در موبایل بهینه کنید")
                
    except Exception as e:
        logging.error(f"❌ خطای غیرمنتظره: {str(e)}")
    finally:
        try:
            content_db.disconnect()
            logging.info("\nاتصال به دیتابیس بسته شد.")
        except:
            logging.error("❌ خطا در بستن اتصال به دیتابیس") 