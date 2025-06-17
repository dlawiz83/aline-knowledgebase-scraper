# Aline Knowledgebase Scraper

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Size](https://img.shields.io/github/languages/code-size/dlawiz83/aline-knowledgebase-scraper)]()

---

## 📖 Project Overview

This project is a **robust, reusable scraper** that extracts technical knowledge from various sources, including:

- PDF book chapters (Aline’s book, chapters 1 to 8)
- Interviewing.io blog posts and guides
- Nil Mamano’s DS&A blog posts
- Generic blogs (configurable selectors)

It compiles all scraped content into a **standardized JSON knowledgebase** format for use in AI-driven comment generation tools.

---

## 🧠 Thinking Process & Design Decisions

I built this scraper with **scalability and reusability** as core principles:

- **Base Scraper Class:** To keep code DRY and modular, each source scraper inherits common logic.
- **Dynamic PDF Chapter Extraction:** Uses regex to detect chapters dynamically rather than relying on fixed pages.
- **Tailored Blog Scrapers:** Specific scrapers for each blog’s unique structure, plus a configurable generic scraper.
- **Markdown Conversion:** Converts HTML content to Markdown for readability and consistency.
- **Error Handling & Logging:** To ensure maintainability and quick debugging when sources change.
- **Configurable & Extensible:** Easy to add new sources by extending the base scraper or configuring selectors.

This approach ensures the tool can scale to future customers and various content types without heavy customization.

---

## ⚙️ Installation & Usage
### Prerequisites

- Python 3.8 or newer
- Install dependencies:
  pip install requests beautifulsoup4 pdfplumber

### Usage

Place your PDF file (e.g., Aline_Book_First8Chapters.pdf) in the project directory.

Run the scraper:
python scraper.py

The script will produce a JSON file aline_knowledgebase_output.json containing all scraped items.

### 📂 Output Format
- Each item in the JSON file includes:

- title: The title of the content item

- content: Markdown formatted content

- content_type: Type of content (e.g., book, blog)

- source_url: URL source (if applicable)

- author: Author’s name (if available)

- user_id: Empty string for now (reserved for future use)






