# Test Job Boards for GigSniper

This repository contains test job board pages that simulate various company career sites. These pages are used for testing the GigSniper application's ability to monitor and scrape job listings from different websites.

## Purpose

The test job boards in this repository serve several purposes:

1. **Development Testing**: Provides consistent test cases for developing and testing the GigSniper application
2. **UI/UX Variations**: Simulates different layouts and designs that real job boards might use
3. **Scraping Algorithm Testing**: Helps test the robustness of scraping algorithms against various HTML structures
4. **Demo Environment**: Creates a controlled environment for demonstrating the application's capabilities

## Repository Structure

Each company has its own directory with an `index.html` file that represents their job board:

```
testjobsboard/
├── README.md
├── company-a/
│   └── index.html
├── company-b/
│   └── index.html
└── startup-c/
    └── index.html
```

## Test Companies

### Company A
A traditional corporate job board with a formal structure and multiple departments.

### Company B
A modern tech company with a more dynamic layout and filtering options.

### Startup C
A minimalist startup job board with a clean, simple design.

## Usage

To use these test pages:

1. Clone this repository
2. Open the HTML files in a browser to view them
3. Use these pages as targets for testing the GigSniper application's monitoring capabilities

## Modifying Test Pages

When modifying these test pages to simulate job changes:

1. Add or remove job listings to test the application's ability to detect new or removed positions
2. Change job details to test the application's ability to detect updates to existing positions
3. Modify the HTML structure to test the application's robustness against layout changes

## Notes

- These pages use Tailwind CSS for styling, loaded via CDN
- All links are non-functional (href="#") as these are test pages
- The pages are designed to be static HTML with no backend functionality

## Available Test Pages

- [Company A Careers](./company-a/index.html) - A simple careers page with multiple job listings
- [Company B Jobs](./company-b/index.html) - A job board with filtering options and detailed job descriptions
- [Startup C Opportunities](./startup-c/index.html) - A minimalist startup job page that changes frequently

## How to Use

These pages can be accessed directly via GitHub Pages at:
https://kappachan.github.io/testjobsboard/

You can use these URLs as monitoring targets in the GigSniper application.

## Making Changes

To simulate new job postings or changes to existing listings:
1. Edit the HTML files in the respective company directories
2. Commit and push the changes to GitHub
3. The changes will be reflected on the GitHub Pages site

## License

This project is for testing purposes only. The HTML templates are provided under the MIT license. 