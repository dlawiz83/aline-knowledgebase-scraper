import re
import json
import logging
import requests
import pdfplumber
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(filename='aline_scraper.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


# --- Base Reusable Scraper ---
class BaseScraper:
    def to_item(self, title, content, content_type, url, author=""):
        return {
            "title": title,
            "content": content.strip(),
            "content_type": content_type,
            "source_url": url,
            "author": author,
            "user_id": ""
        }


# --- Markdown Formatter ---
def html_to_markdown(content_div):
    if not content_div:
        return ""

    md_lines = []
    # Walk through all tags of interest in order
    for elem in content_div.find_all(["h1", "h2", "h3", "p", "li"], recursive=True):
        tag = elem.name
        text = elem.get_text(separator=" ").strip()
        if not text:
            continue
        if tag == "h1":
            md_lines.append(f"# {text}")
        elif tag == "h2":
            md_lines.append(f"## {text}")
        elif tag == "h3":
            md_lines.append(f"### {text}")
        elif tag == "li":
            md_lines.append(f"- {text}")
        else:
            md_lines.append(text)
        md_lines.append("")
    return "\n".join(md_lines)


# --- PDF Book Extractor ---
class PDFBookExtractor(BaseScraper):
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.chapter_pattern = re.compile(r'chapter\s*(\d+)', re.IGNORECASE)

    def extract_chapters(self, max_chapters=8):
        chapters = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                chapter_starts = []

                # Scan all pages for chapter headings
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        match = self.chapter_pattern.search(line)
                        if match:
                            chap_num = int(match.group(1))
                            # Save chapter start only if not already saved for that chapter
                            if not any(c[1] == chap_num for c in chapter_starts):
                                chapter_starts.append((i, chap_num, line.strip()))
                                logging.info(f"Found chapter {chap_num} start on page {i+1}")

                # Sort chapters by number
                chapter_starts.sort(key=lambda x: x[1])

                # If chapter 1 missing, forcibly add first page as chapter 1 start
                if not any(c[1] == 1 for c in chapter_starts):
                    chapter_starts.insert(0, (0, 1, "Chapter 1"))

                # Extract chapter text per page range
                for idx, (start_page, chap_num, chap_title) in enumerate(chapter_starts[:max_chapters]):
                    end_page = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(pdf.pages)
                    chapter_text = "\n".join(pdf.pages[p].extract_text() or "" for p in range(start_page, end_page)).strip()
                    chapters.append((f"Chapter {chap_num}: {chap_title}", chapter_text))

        except Exception as e:
            logging.error(f"PDF extraction error: {e}")
        return chapters

    def scrape(self):
        return [self.to_item(title, content, "book", self.pdf_path) for title, content in self.extract_chapters()]


# --- Interviewing.io Blog Scraper ---
class InterviewingIOBlogScraper(BaseScraper):
    BASE_URL = "https://interviewing.io/blog"

    def get_post_links(self):
        res = requests.get(self.BASE_URL)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        links = []
        # The blog might use article tags or other containers, try generic link finding under blog path
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/blog/" in href and href not in links:
                full_url = urljoin(self.BASE_URL, href)
                if full_url not in links:
                    links.append(full_url)
        logging.info(f"Interviewing.io blog found {len(links)} posts")
        return links

    def scrape_post(self, url):
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "No Title"
        content_div = soup.find("div", class_="prose") or soup.find("article") or soup.body
        content = html_to_markdown(content_div)
        return self.to_item(title, content, "blog", url)

    def scrape(self):
        posts = []
        links = self.get_post_links()
        for url in links:
            try:
                posts.append(self.scrape_post(url))
            except Exception as e:
                logging.error(f"Error scraping post {url}: {e}")
        return posts


# --- Nil Mamano DSA Blog Scraper ---
class NilMamanoDSAScraper(BaseScraper):
    BASE_URL = "https://nilmamano.com/blog/category/dsa"

    def get_post_links(self):
        page_url = self.BASE_URL
        links = []
        while page_url:
            res = requests.get(page_url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            new_links = [a["href"] for a in soup.select("h2.entry-title a")]
            for link in new_links:
                if link not in links:
                    links.append(link)
            next_btn = soup.select_one("a.next.page-numbers")
            page_url = next_btn["href"] if next_btn else None
        logging.info(f"Nil Mamano DSA blog found {len(links)} posts")
        return links

    def scrape_post(self, url):
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.find("h1", class_="entry-title")
        title = title_tag.text.strip() if title_tag else "No Title"
        content_div = soup.find("div", class_="entry-content")
        content = html_to_markdown(content_div)
        return self.to_item(title, content, "blog", url, author="Nil Mamano")

    def scrape(self):
        posts = []
        links = self.get_post_links()
        for url in links:
            try:
                posts.append(self.scrape_post(url))
            except Exception as e:
                logging.error(f"Error scraping Nil Mamano post {url}: {e}")
        return posts


# --- Generic Blog Scraper ---
class GenericBlogScraper(BaseScraper):
    def __init__(self, base_url, post_selector, title_selector, content_selector):
        self.base_url = base_url
        self.post_selector = post_selector
        self.title_selector = title_selector
        self.content_selector = content_selector

    def get_post_links(self):
        res = requests.get(self.base_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        links = []
        for a in soup.select(self.post_selector):
            href = a.get("href")
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in links:
                    links.append(full_url)
        logging.info(f"Generic blog found {len(links)} posts at {self.base_url}")
        return links

    def scrape_post(self, url):
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.select_one(self.title_selector)
        title = title_tag.text.strip() if title_tag else "No Title"
        content_div = soup.select_one(self.content_selector)
        content = html_to_markdown(content_div)
        return self.to_item(title, content, "blog", url)

    def scrape(self):
        posts = []
        links = self.get_post_links()
        for url in links:
            try:
                posts.append(self.scrape_post(url))
            except Exception as e:
                logging.error(f"Error scraping generic blog post {url}: {e}")
        return posts


# --- Main Execution ---
def main():
    all_items = []

    # PDF Book extraction
    pdf_scraper = PDFBookExtractor("Aline_Book_First8Chapters.pdf")
    book_items = pdf_scraper.scrape()
    logging.info(f"Extracted {len(book_items)} chapters from book")
    all_items.extend(book_items)

    # Interviewing.io blog scraping
    interviewing_scraper = InterviewingIOBlogScraper()
    interviewing_items = interviewing_scraper.scrape()
    logging.info(f"Extracted {len(interviewing_items)} items from interviewing.io blog")
    all_items.extend(interviewing_items)

    # Nil Mamano DSA blog scraping
    nil_scraper = NilMamanoDSAScraper()
    nil_items = nil_scraper.scrape()
    logging.info(f"Extracted {len(nil_items)} items from Nil Mamano DSA blog")
    all_items.extend(nil_items)

    # Generic blog scraping example (Quill)
    generic_scraper = GenericBlogScraper(
        base_url="https://quill.co/blog",
        post_selector="a.card-title",
        title_selector="h1",
        content_selector="div.article-content"
    )
    generic_items = generic_scraper.scrape()
    logging.info(f"Extracted {len(generic_items)} items from generic blog")
    all_items.extend(generic_items)

    # Prepare final JSON output
    result = {
        "team_id": "aline123",
        "items": all_items
    }

    with open("aline_knowledgebase_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f" Done! Extracted {len(all_items)} items.")


if __name__ == "__main__":
    main()
